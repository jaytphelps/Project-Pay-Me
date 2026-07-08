from abc import ABC, abstractmethod


class Job(ABC):
    name = ""

    @abstractmethod
    def run(self, **kwargs):
        f'execute the job with args {kwargs}.'
        pass