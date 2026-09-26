"""Record a WebM walkthrough of freshly executed demo results using Chrome.

Run with Python having websockets installed; demos run under --python.
The video labels itself a replay of measured results, rather than live terminal capture.
"""

import argparse
import base64
import json
import subprocess
import time
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.request import urlopen


def main() -> None:
    from websockets.sync.client import connect

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--python', type=Path, default=Path('.venv/Scripts/python.exe'))
    parser.add_argument(
        '--chrome', type=Path, default=Path('C:/Program Files/Google/Chrome/Application/chrome.exe')
    )
    parser.add_argument('--output', type=Path, default=Path('docs/demo/smriti-demo.webm'))
    args = parser.parse_args()
    reports = []
    for name in ('index', 'context', 'sessions', 'memory_history'):
        command = [str(args.python.resolve()), f'scripts/demo_{name}.py']
        if name == 'index':
            command += ['--files', '20']
        started = time.perf_counter()
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        reports.append(
            {
                'demo': name,
                'wall_seconds': time.perf_counter() - started,
                'result': json.loads(result.stdout),
            }
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.with_suffix('.json').write_text(
        json.dumps(reports, indent=2) + '\n', encoding='utf-8'
    )
    with TemporaryDirectory(prefix='smriti-demo-chrome-', ignore_cleanup_errors=True) as directory:
        profile = Path(directory)
        browser = subprocess.Popen(
            [
                str(args.chrome),
                '--headless=new',
                '--disable-gpu',
                '--no-first-run',
                '--remote-debugging-port=0',
                f'--user-data-dir={profile}',
                'about:blank',
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        try:
            endpoint = profile / 'DevToolsActivePort'
            deadline = time.monotonic() + 30
            while not endpoint.exists():
                if time.monotonic() > deadline or browser.poll() is not None:
                    raise RuntimeError('Chrome debugging endpoint did not start')
                time.sleep(0.1)
            port = endpoint.read_text().splitlines()[0]
            with urlopen(f'http://127.0.0.1:{port}/json', timeout=10) as response:
                page = json.load(response)[0]
            time.sleep(2)
            with connect(page['webSocketDebuggerUrl'], max_size=32 * 1024 * 1024) as socket:
                expression = """(async () => {
 const reports = REPORTS;
 const canvas = document.createElement('canvas'); canvas.width=1280; canvas.height=720;
 document.body.append(canvas); const ctx=canvas.getContext('2d');
 const stream=canvas.captureStream(10);
 const mime=['video/webm;codecs=vp9','video/webm;codecs=vp8','video/webm'].find(x=>MediaRecorder.isTypeSupported(x));
 if (!mime) throw Error('No WebM encoder');
 const recorder=new MediaRecorder(stream,{mimeType:mime,videoBitsPerSecond:1500000});
 const chunks=[]; recorder.ondataavailable=e=>{if(e.data.size)chunks.push(e.data)};
 const stopped=new Promise(resolve=>recorder.onstop=resolve); recorder.start();
 for(const report of reports){
  ctx.fillStyle='#101716';ctx.fillRect(0,0,1280,720);
  ctx.fillStyle='#b8e5b1';ctx.font='bold 40px monospace';ctx.fillText('SMRITI / '+report.demo,48,64);
  ctx.fillStyle='#c8d6cf';ctx.font='20px monospace';ctx.fillText('Replay of freshly measured results; synthetic fixtures',48,104);
  const compact = report.demo==='memory_history' ? {
   wall_seconds:report.wall_seconds, rename_preserved_id:report.result.rename_preserved_id,
   freshness:report.result.stale_fact.freshness, reason:report.result.stale_fact.freshness_reason,
   conflict_blocked:report.result.conflict_blocked, merged_text:report.result.merged_text,
   restored_text:report.result.restored_text, merge_operation:report.result.merge_operation,
   revert_operation:report.result.revert_operation, scope:report.result.scope
  } : report;
  const lines=JSON.stringify(compact,null,2).split('\\n');ctx.font='17px monospace';
  lines.slice(0,25).forEach((line,i)=>ctx.fillText(line.slice(0,116),48,150+i*21));
  await new Promise(resolve=>setTimeout(resolve,5000));
 }
 recorder.stop();await stopped;stream.getTracks().forEach(track=>track.stop());
 const blob=new Blob(chunks,{type:mime});const bytes=new Uint8Array(await blob.arrayBuffer());
 let binary='';for(let i=0;i<bytes.length;i+=32768)binary+=String.fromCharCode(...bytes.subarray(i,i+32768));
 return {base64:btoa(binary),preview:canvas.toDataURL('image/png').split(',')[1],mime,bytes:bytes.length,duration_seconds:20};
})()""".replace('REPORTS', json.dumps(reports))
                socket.send(
                    json.dumps(
                        {
                            'id': 1,
                            'method': 'Runtime.evaluate',
                            'params': {
                                'expression': expression,
                                'awaitPromise': True,
                                'returnByValue': True,
                            },
                        }
                    )
                )
                while True:
                    message = json.loads(socket.recv(timeout=60))
                    if message.get('id') == 1:
                        break
                if 'exceptionDetails' in message.get('result', {}):
                    raise RuntimeError(message['result']['exceptionDetails'])
                if 'error' in message:
                    raise RuntimeError(message['error'])
                recorded = message['result']['result']['value']
                args.output.with_suffix('.png').write_bytes(
                    base64.b64decode(recorded.pop('preview'), validate=True)
                )
                video = base64.b64decode(recorded.pop('base64'), validate=True)
                if len(video) < 1000:
                    raise RuntimeError('Recording is unexpectedly empty')
                args.output.write_bytes(video)
                print(json.dumps({'output': str(args.output), **recorded}, indent=2))
        finally:
            browser.terminate()
            browser.wait(timeout=15)


if __name__ == '__main__':
    main()
