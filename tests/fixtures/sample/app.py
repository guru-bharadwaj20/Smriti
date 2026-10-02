"""Fixture repository with known graph structure."""


class Base:
    def normalize(self, value: str) -> str:
        return value.strip()


class Processor(Base):
    def process(self, value: str) -> str:
        return self.normalize(value).upper()


def run(value: str) -> str:
    return Processor().process(value)
