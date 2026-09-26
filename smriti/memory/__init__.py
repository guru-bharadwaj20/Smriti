"""Durable, repository-local facts for coding agents."""
from dataclasses import dataclass, asdict, replace
import json
import sqlite3
import uuid
import math
from datetime import datetime, timezone, timedelta
from .operations import OperationLog, canonical
from .temporal import Timeline, TemporalVersion, ValidInterval, TransactionInterval, timestamp
import datetime as _dt


@dataclass(frozen=True)
class Anchor:
    symbol_id: str
    content_hash: str = ""


@dataclass(frozen=True)
class Fact:
    id: str
    text: str
    user: str | None = None
    session: str | None = None
    tool: str | None = None
    source: str | None = None
    confidence: float = 1.0
    anchors: tuple[Anchor, ...] = ()
    freshness: str = 'fresh'
    freshness_reason: str | None = None
    triggering_commit: str | None = None
    subject: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    recorded_at: str | None = None
    created_at: str | None = None

    def to_dict(self):
        return {**asdict(self), 'scope': self.scope, 'requires_revalidation': self.freshness != 'fresh'}

    @property
    def scope(self):
        return 'symbol' if self.anchors else 'project'


class MemoryStore:
    """SQLite-backed fact store. Each write is atomic and survives restart."""

    def __init__(self, db_path, *, clock=None):
        self.db = sqlite3.connect(str(db_path))
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        schemas = [
            "CREATE TABLE IF NOT EXISTS facts (id TEXT PRIMARY KEY, payload TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS fact_anchors (fact_id TEXT, symbol_id TEXT, content_hash TEXT, PRIMARY KEY (fact_id, symbol_id))",
            "CREATE TABLE IF NOT EXISTS fact_audit (seq INTEGER PRIMARY KEY, fact_id TEXT, before_payload TEXT, after_payload TEXT)",
            "CREATE TABLE IF NOT EXISTS conflict_audit (seq INTEGER PRIMARY KEY, fact_id TEXT, candidate_ids TEXT, winner_id TEXT)",
            "CREATE TABLE IF NOT EXISTS memory_meta (key TEXT PRIMARY KEY, value TEXT)",
        ]
        for sql in schemas:
            self.db.execute(sql)
        self.db.execute("INSERT OR IGNORE INTO memory_meta VALUES ('head',NULL)")
        self.db.commit()
        self.operations = OperationLog(self.db)
        self.db.execute("CREATE TABLE IF NOT EXISTS memory_branches (name TEXT PRIMARY KEY,head TEXT)")
        self.db.execute("INSERT OR IGNORE INTO memory_meta VALUES ('branch','main')")
        self.db.execute("INSERT OR IGNORE INTO memory_branches VALUES ('main',?)",(self.head,))
        self.db.execute("CREATE TABLE IF NOT EXISTS memory_purged (fact_id TEXT PRIMARY KEY)")
        self.db.commit()

    def close(self):
        self.db.close()

    def remember(self, text, *, fact_id=None, user=None, session=None, tool=None,
                 source=None, confidence=1.0, anchors=(), selected_context=(), subject=None,
                 valid_from=None, valid_to=None):
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Fact text must be nonempty")
        if not isinstance(confidence, (int,float)) or not math.isfinite(confidence) or not 0 <= confidence <= 1:
            raise ValueError("Confidence must be finite in [0,1]")
        for value in (user,session,tool,source,subject):
            if value is not None and (not isinstance(value,str) or not value.strip()):
                raise ValueError("Metadata values must be nonempty strings")
        if not anchors:
            anchors = tuple(Anchor(s["symbol_id"],s["content_hash"]) if isinstance(s,dict) else Anchor(s.id,s.content_hash) for s in selected_context)
        anchors = tuple(Anchor(**a) if isinstance(a,dict) else a for a in anchors)
        if any(not isinstance(a,Anchor) or not a.symbol_id or not a.content_hash for a in anchors):
            raise ValueError("Anchors require symbol IDs and hashes")
        if len({a.symbol_id for a in anchors}) != len(anchors):
            raise ValueError("Duplicate anchors are not allowed")
        if self.is_purged(fact_id):
            raise ValueError("Forgotten fact IDs cannot be reused")
        recorded_at = self._event_time()
        valid = ValidInterval(valid_from or recorded_at, valid_to)
        fact = Fact(fact_id or uuid.uuid4().hex,text,user,session,tool,source,float(confidence),anchors)
        fact = replace(fact,subject=subject,created_at=recorded_at,valid_from=valid.start.isoformat(),valid_to=valid.end.isoformat() if valid.end else None,recorded_at=recorded_at)
        with self.db:
            self.db.execute("INSERT INTO facts VALUES (?,?)",(fact.id,canonical(asdict(fact))))
            self.db.executemany("INSERT INTO fact_anchors VALUES (?,?,?)",[(fact.id,a.symbol_id,a.content_hash) for a in anchors])
            self._record("add",fact.id,asdict(fact),recorded_at=recorded_at)
        return fact

    def recall(self,query="",*,valid_at=None,as_of=None,include_stale=True):
        if valid_at is None and as_of is None:
            facts = [self._decode(row[0]) for row in self.db.execute("SELECT payload FROM facts ORDER BY id")]
        else:
            now = timestamp(self._clock())
            facts = [self._decode(canonical(v.payload)) for v in self.timeline().query(valid_at or now,as_of or now)]
        return self._rank_recall(facts,query,include_stale)

    @staticmethod
    def _decode(payload):
        data = json.loads(payload)
        data["anchors"] = tuple(Anchor(**a) for a in data.get("anchors", ()))
        return Fact(**data)

# P09.05

# P09.06

# P09.07

# P09.08
    def _save(self,fact):
        fact = replace(fact,recorded_at=self._event_time())
        with self.db:
            previous = self.db.execute("SELECT payload FROM facts WHERE id=?",(fact.id,)).fetchone()
            if previous is None:
                raise KeyError(fact.id)
            self.db.execute("INSERT INTO fact_audit(fact_id,before_payload,after_payload) VALUES (?,?,?)",(fact.id,previous[0],canonical(asdict(fact))))
            self.db.execute("UPDATE facts SET payload=? WHERE id=?",(canonical(asdict(fact)),fact.id))
            self.db.execute("DELETE FROM fact_anchors WHERE fact_id=?",(fact.id,))
            self.db.executemany("INSERT INTO fact_anchors VALUES (?,?,?)",[(fact.id,a.symbol_id,a.content_hash) for a in fact.anchors])
            self._record("update",fact.id,asdict(fact),recorded_at=fact.recorded_at)
        return fact

    def refresh(self, symbols, *, renames=None, commit=None):
        """symbols maps stable symbol IDs to current content hashes."""
        renames = renames or {}
        changes = []
        for fact in self.recall():
            moved = tuple(Anchor(renames[a.symbol_id], a.content_hash) if a.symbol_id in renames and symbols.get(renames[a.symbol_id]) == a.content_hash else a for a in fact.anchors)
            if moved != fact.anchors:
                fact = self._save(replace(fact, anchors=moved))
                changes.append(fact)
            if any(a.symbol_id not in symbols for a in fact.anchors):
                changes.append(self._save(replace(fact, freshness='orphaned', freshness_reason='anchor_deleted', triggering_commit=commit)))
            elif any(a.symbol_id in symbols and symbols[a.symbol_id] != a.content_hash for a in fact.anchors):
                changes.append(self._save(replace(fact, freshness="stale", freshness_reason="anchor_changed", triggering_commit=commit)))
        return changes
# P09.09

# P09.10

# P09.11

# P09.12
    def anchor_states(self, fact_id, symbols):
        fact = next((f for f in self.recall() if f.id == fact_id), None)
        if fact is None:
            raise KeyError(fact_id)
        return {a.symbol_id: ("orphaned" if a.symbol_id not in symbols else "fresh" if symbols[a.symbol_id] == a.content_hash else "stale") for a in fact.anchors}
# P09.13

# P09.14

# P09.15
    def revalidate(self, fact_id, symbols, *, commit=None):
        fact = next((f for f in self.recall() if f.id == fact_id), None)
        if fact is None:
            raise KeyError(fact_id)
        if any(a.symbol_id not in symbols for a in fact.anchors):
            raise ValueError("Cannot revalidate a deleted anchor")
        anchors = tuple(Anchor(a.symbol_id, symbols[a.symbol_id]) for a in fact.anchors)
        return self._save(replace(fact, anchors=anchors, freshness="fresh", freshness_reason="revalidated", triggering_commit=commit))

    def audit(self, fact_id):
        return [{"before": self._decode(before) if before else None, "after": self._decode(after)} for before, after in self.db.execute("SELECT before_payload,after_payload FROM fact_audit WHERE fact_id=? ORDER BY seq", (fact_id,))]
# P09.16
    def contradictions(self, fact_id):
        fact = next((f for f in self.recall() if f.id == fact_id), None)
        if fact is None:
            raise KeyError(fact_id)
        if not fact.subject:
            return []
        return [f for f in self.recall() if f.id != fact.id and f.subject == fact.subject and f.text != fact.text]
# P09.17
    @staticmethod
    def relatedness(left, right, left_vector, right_vector):
        if len(left_vector) != len(right_vector) or not left_vector:
            raise ValueError("Embedding dimensions must match and be nonempty")
        if not all(math.isfinite(x) for x in (*left_vector, *right_vector)):
            raise ValueError("Embeddings must be finite")
        norm = math.sqrt(sum(x*x for x in left_vector) * sum(x*x for x in right_vector))
        cosine = sum(x*y for x, y in zip(left_vector, right_vector)) / norm if norm else 0.0
        a, b = {x.symbol_id for x in left.anchors}, {x.symbol_id for x in right.anchors}
        overlap = len(a & b) / len(a | b) if a | b else 0.0
        return 0.7 * max(0.0, cosine) + 0.3 * overlap
# P09.18
    def preferred(self, fact_id, source_priority=None):
        fact = next((f for f in self.recall() if f.id == fact_id), None)
        if fact is None:
            raise KeyError(fact_id)
        priorities = source_priority or {"code": 3, "test": 2, "user": 1}
        candidates = [fact, *self.contradictions(fact_id)]
        winner = max(candidates, key=lambda f: (priorities.get(f.source, 0), *self._revision_order(f), f.confidence, f.id))
        with self.db:
            self.db.execute("INSERT INTO conflict_audit(fact_id,candidate_ids,winner_id) VALUES (?,?,?)", (fact_id, json.dumps(sorted(f.id for f in candidates)), winner.id))
        return winner
# P09.19
    def conflict_history(self, fact_id):
        return [{"candidates": json.loads(c), "winner": w} for c, w in self.db.execute("SELECT candidate_ids,winner_id FROM conflict_audit WHERE fact_id=? ORDER BY seq", (fact_id,))]
# P09.20

# P09.21
    def _rank_recall(self, facts: list[Fact], query: str, include_stale: bool) -> list[Fact]:
        facts=[f for f in facts if include_stale or f.freshness=="fresh"]
        scores: dict[str, float]
        if query.strip():
            from ..lexical.index import BM25Index
            index=BM25Index()
            for fact in facts:
                index.add(fact.id,{"signature":" ".join(a.symbol_id for a in fact.anchors),"docstring":fact.subject or "","body":fact.text})
            scores={hit.id:hit.score for hit in index.search(query,k=len(facts))}
            facts=[f for f in facts if f.id in scores]
        else:
            scores={}
        return sorted(facts,key=lambda f: ({"fresh":0,"stale":1,"orphaned":2}[f.freshness],-scores.get(f.id,0.0),-f.confidence,f.id))

    def _revision_order(self, fact: Fact) -> tuple[str, str, int]:
        # Persisted insertion order is the fallback for pre-timestamp facts.
        row = self.db.execute("SELECT rowid FROM facts WHERE id=?", (fact.id,)).fetchone()
        valid_from = getattr(fact, "valid_from", None) or fact.created_at or ""
        recorded_at = getattr(fact, "recorded_at", None) or fact.created_at or ""
        return str(valid_from), str(recorded_at), int(row[0]) if row else 0
    @property
    def head(self):
        return self.db.execute("SELECT value FROM memory_meta WHERE key='head'").fetchone()[0]

    def _event_time(self):
        point=timestamp(self._clock())
        if self.head:
            prior=timestamp(self.operations.get(self.head).recorded_at)
            if point<=prior:
                point=prior+timedelta(microseconds=1)
        return point.isoformat()

    def _record(self,kind,fact_id=None,payload=None,*,metadata=None,recorded_at=None,parents=None):
        op = self.operations.append_uncommitted(kind,fact_id,payload,parents=parents if parents is not None else ((self.head,) if self.head else ()),recorded_at=recorded_at or self._event_time(),metadata=metadata)
        self.db.execute("UPDATE memory_meta SET value=? WHERE key='head'",(op.id,))
        self.db.execute("UPDATE memory_branches SET head=? WHERE name=?",(op.id,self.current_branch))
        return op

    def replay(self,head=None):
        state = {}
        for op in self.operations.ancestry(head if head is not None else self.head):
            if op.kind in ("merge","restore"):
                state={}
                for fid,payload_hash in op.metadata["state"].items():
                    row=self.db.execute("SELECT payload FROM memory_blobs WHERE digest=?",(payload_hash,)).fetchone()
                    if row and not self.is_purged(fid):
                        state[fid]=self._decode(row[0])
                continue
            if self.is_purged(op.fact_id):
                continue
            if op.kind == "revert":
                payload=self.operations.payload(op)
                if payload is None:
                    state.pop(op.fact_id,None)
                else:
                    state[op.fact_id]=self._decode(canonical(payload))
            elif op.kind == "invalidate":
                state.pop(op.fact_id,None)
            elif op.kind in ("add","update"):
                payload = self.operations.payload(op)
                if payload is not None:
                    state[op.fact_id] = self._decode(canonical(payload))
        return state
# P10.12
    def update(self,fact_id,text=None,*,valid_from=None,valid_to=None):
        fact = next((f for f in self.recall() if f.id==fact_id),None)
        if fact is None:
            raise KeyError(fact_id)
        if text is not None and (not isinstance(text,str) or not text.strip()):
            raise ValueError("Fact text must be nonempty")
        valid = ValidInterval(valid_from or fact.valid_from,valid_to if valid_to is not None else fact.valid_to)
        return self._save(replace(fact,text=text if text is not None else fact.text,valid_from=valid.start.isoformat(),valid_to=valid.end.isoformat() if valid.end else None))

    def timeline(self,head=None):
        timeline=Timeline()
        chain=[]
        cursor=self.head if head is None else head
        while cursor:
            op=self.operations.get(cursor)
            chain.append(op)
            cursor=op.parents[0] if op.parents else None
        def retire(fact_id,at,keep_past=False):
            rows=[]
            additions=[]
            for old in timeline.rows:
                if old.transaction.end is not None or (fact_id is not None and old.fact_id!=fact_id):
                    rows.append(old)
                    continue
                rows.append(replace(old,transaction=TransactionInterval(old.transaction.start,at)))
                end=min(old.valid.end,at) if old.valid.end is not None else at
                if keep_past and old.valid.start<end:
                    additions.append(TemporalVersion(old.fact_id,dict(old.payload),ValidInterval(old.valid.start,end),TransactionInterval(at)))
            timeline.rows=rows+additions
        for op in reversed(chain):
            if self.is_purged(op.fact_id):
                continue
            at=timestamp(op.recorded_at)
            if op.kind in ("merge","restore"):
                retire(None,at)
                for fid,h in op.metadata["state"].items():
                    row=self.db.execute("SELECT payload FROM memory_blobs WHERE digest=?",(h,)).fetchone()
                    if row and not self.is_purged(fid):
                        payload=json.loads(row[0])
                        timeline.correct(fid,payload,ValidInterval(payload["valid_from"],payload.get("valid_to")),at)
            elif op.kind=="invalidate":
                retire(op.fact_id,at,True)
            elif op.kind in ("add","update","revert"):
                payload=self.operations.payload(op)
                if payload is not None:
                    timeline.correct(op.fact_id,payload,ValidInterval(payload["valid_from"],payload.get("valid_to")),at)
                elif op.kind=="revert":
                    retire(op.fact_id,at)
        timeline.rows=[v for v in timeline.rows if not self.is_purged(v.fact_id)]
        return timeline
# P10.13
    def invalidate(self,fact_id,*,reason="invalidated"):
        fact = next((f for f in self.recall() if f.id==fact_id),None)
        if fact is None:
            raise KeyError(fact_id)
        with self.db:
            from .operations import digest
            self._record("invalidate",fact_id,{"id":fact_id,"reason":reason},metadata={"reason_hash":digest(reason)})
            self.db.execute("DELETE FROM facts WHERE id=?",(fact_id,))
            self.db.execute("DELETE FROM fact_anchors WHERE fact_id=?",(fact_id,))
        return fact_id
# P10.14
    def is_purged(self,fact_id):
        return fact_id is not None and self.db.execute("SELECT 1 FROM memory_purged WHERE fact_id=?",(fact_id,)).fetchone() is not None

    def forget(self,fact_id):
        if self.is_purged(fact_id):
            return []
        exists = self.db.execute("SELECT 1 FROM memory_operations WHERE json_extract(canonical,'$.fact_id')=?",(fact_id,)).fetchone()
        if not exists:
            raise KeyError(fact_id)
        with self.db:
            self.db.execute("INSERT INTO memory_purged VALUES (?)",(fact_id,))
            hashes = [self.operations.get(oid).payload_hash for (oid,) in self.db.execute("SELECT oid FROM memory_operations WHERE json_extract(canonical,'$.fact_id')=?",(fact_id,))]
            self.db.executemany("DELETE FROM memory_blobs WHERE digest=?",[(h,) for h in hashes if h])
            self.db.execute("DELETE FROM facts WHERE id=?",(fact_id,))
            self.db.execute("DELETE FROM fact_anchors WHERE fact_id=?",(fact_id,))
            self.db.execute("DELETE FROM fact_audit WHERE fact_id=?",(fact_id,))
            self.db.execute("DELETE FROM conflict_audit WHERE fact_id=? OR winner_id=? OR candidate_ids LIKE ?",(fact_id,fact_id,"%"+fact_id+"%"))
            self._record("forget",fact_id)
        return [fact_id]
# P10.15
    def replay_digest(self,head=None):
        from .operations import digest
        return digest({fid:asdict(f) for fid,f in sorted(self.replay(head).items())})
# P10.16
    def log(self,*,head=None,limit=None):
        rows = [{**op.to_dict(),"payload":None if self.is_purged(op.fact_id) else self.operations.payload(op)} for op in reversed(self.operations.ancestry(head if head is not None else self.head))]
        return rows[:limit] if limit is not None else rows
# P10.17
    def diff(self,left,right=None):
        a,b=self.replay(left) if left else {},self.replay(right if right is not None else self.head)
        return {"added":{k:b[k].to_dict() for k in sorted(b.keys()-a.keys())},"removed":{k:a[k].to_dict() for k in sorted(a.keys()-b.keys())},"changed":{k:{"before":a[k].to_dict(),"after":b[k].to_dict()} for k in sorted(a.keys()&b.keys()) if a[k]!=b[k]}}
# P10.18
    def _materialize(self,state):
        self.db.execute("DELETE FROM facts")
        self.db.execute("DELETE FROM fact_anchors")
        for fact in state.values():
            if self.is_purged(fact.id):
                continue
            self.db.execute("INSERT INTO facts VALUES (?,?)",(fact.id,canonical(asdict(fact))))
            self.db.executemany("INSERT INTO fact_anchors VALUES (?,?,?)",[(fact.id,a.symbol_id,a.content_hash) for a in fact.anchors])

    def revert(self,operation_id):
        op=self.operations.get(operation_id)
        if any(o.metadata.get("reverts")==operation_id for o in self.operations.ancestry(self.head)):
            raise ValueError("Operation was already reverted")
        if operation_id not in {o.id for o in self.operations.ancestry(self.head)}:
            raise ValueError("Operation is not on the active branch")
        if op.kind not in ("add","update","invalidate"):
            raise ValueError("Operation kind is not reversible")
        if self.is_purged(op.fact_id):
            raise ValueError("Forgotten payloads cannot be restored")
        before=self.replay(op.parents[0]) if op.parents else {}
        prior=before.get(op.fact_id)
        with self.db:
            inverse=self._record("revert",op.fact_id,asdict(prior) if prior else None,metadata={"reverts":operation_id})
            self._materialize(self.replay())
        return inverse.id
# P10.19

# P10.20

# P10.21
    def verify(self):
        stored={row[0]:self._decode(row[1]) for row in self.db.execute("SELECT id,payload FROM facts")}
        expected=self.replay()
        if stored!=expected:
            raise ValueError("Materialized memory differs from verified operation replay")
        return True
# P10.22

# P10.23
    @property
    def current_branch(self):
        return self.db.execute("SELECT value FROM memory_meta WHERE key='branch'").fetchone()[0]

    def branches(self):
        return dict(self.db.execute("SELECT name,head FROM memory_branches ORDER BY name"))
# P11.01
    def common_base(self,left,right):
        common={o.id for o in self.operations.ancestry(left)} & {o.id for o in self.operations.ancestry(right)}
        if not common:
            return None
        candidates=[]
        for oid in common:
            if not any(oid!=other and oid in {a.id for a in self.operations.ancestry(other)} for other in common):
                candidates.append(oid)
        if len(candidates)!=1:
            raise ValueError("Multiple merge bases require explicit resolution")
        return candidates[0]
# P11.02
    @staticmethod
    def _branch_name(name):
        if not isinstance(name,str) or not name or any(c.isspace() or c in "~^:?*[" or c == chr(92) for c in name) or ".." in name or "@{" in name or name.startswith((".", "/")) or name.endswith(("/", ".lock", ".")):
            raise ValueError("Invalid branch name")
        return name

    def branch(self,name,*,from_head=None):
        name=self._branch_name(name)
        head=self.head if from_head is None else (from_head or None)
        if head:
            self.operations.get(head)
        with self.db:
            self.db.execute("INSERT INTO memory_branches VALUES (?,?)",(name,head))
        return head
# P11.03
    def switch(self,name):
        row=self.db.execute("SELECT head FROM memory_branches WHERE name=?",(name,)).fetchone()
        if row is None:
            raise KeyError(name)
        with self.db:
            self.db.execute("UPDATE memory_meta SET value=? WHERE key='branch'",(name,))
            self.db.execute("UPDATE memory_meta SET value=? WHERE key='head'",(row[0],))
            self._materialize(self.replay(row[0]) if row[0] else {})
        return self.head
# P11.04
    def sync_git(self,repository):
        import subprocess
        result=subprocess.run(["git","-C",str(repository),"symbolic-ref","--quiet","--short","HEAD"],capture_output=True,text=True)
        if result.returncode==0:
            name=result.stdout.strip()
        else:
            revision=subprocess.run(["git","-C",str(repository),"rev-parse","--verify","HEAD"],capture_output=True,text=True,check=True).stdout.strip()
            name="detached/"+revision
        if name not in self.branches():
            self.branch(name)
        self.switch(name)
        return name
# P11.05
    def rename_branch(self,old,new):
        new=self._branch_name(new)
        if old not in self.branches():
            raise KeyError(old)
        with self.db:
            self.db.execute("UPDATE memory_branches SET name=? WHERE name=?",(new,old))
            if self.current_branch==old:
                self.db.execute("UPDATE memory_meta SET value=? WHERE key='branch'",(new,))
        return new

    def delete_branch(self,name):
        if name==self.current_branch:
            raise ValueError("Cannot delete the active branch")
        if name not in self.branches():
            raise KeyError(name)
        with self.db:
            self.db.execute("DELETE FROM memory_branches WHERE name=?",(name,))
# P11.06

# P11.07
    @staticmethod
    def _same_fact(left,right):
        if left is None or right is None:
            return left is right
        return replace(left,recorded_at=None)==replace(right,recorded_at=None)

    def merge_preview(self,source):
        if source not in self.branches():
            raise KeyError(source)
        source_head=self.branches()[source]
        base=self.common_base(self.head,source_head)
        ancestor=self.replay(base) if base else {}
        ours=self.replay(self.head) if self.head else {}
        theirs=self.replay(source_head) if source_head else {}
        state,conflicts={},{}
        for fid in sorted(ancestor.keys()|ours.keys()|theirs.keys()):
            if self.is_purged(fid):
                continue
            a,o,t=ancestor.get(fid),ours.get(fid),theirs.get(fid)
            if self._same_fact(o,t):
                selected=o
            elif self._same_fact(o,a):
                selected=t
            elif self._same_fact(t,a):
                selected=o
            else:
                conflicts[fid]={"base":a,"ours":o,"theirs":t}
                continue
            if selected is not None:
                state[fid]=selected
        return {"base":base,"state":state,"conflicts":conflicts,"source_head":source_head}
# P11.08
    def _snapshot(self,kind,state,*,metadata=None,parents=None):
        from .operations import digest
        references={}
        for fid,fact in state.items():
            if self.is_purged(fid):
                continue
            payload=asdict(fact)
            h=digest(payload)
            self.db.execute("INSERT OR IGNORE INTO memory_blobs VALUES (?,?)",(h,canonical(payload)))
            references[fid]=h
        return self._record(kind,metadata={**(metadata or {}),"state":references},parents=parents)

    def merge(self,source,*,resolutions=None):
        preview=self.merge_preview(source)
        if preview["conflicts"]:
            raise ValueError("Merge has unresolved conflicts")
        with self.db:
            op=self._snapshot("merge",preview["state"],metadata={"source":source,"base":preview["base"]})
            self._materialize(preview["state"])
        return op.id
# P11.09
