class Singleton:
    __instances = {}  # noqa: RUF012

    def __new__(cls, *args, **kwargs):
        if cls not in cls.__instances:
            cls.__instances[cls] = object.__new__(cls)
        return cls.__instances[cls]
