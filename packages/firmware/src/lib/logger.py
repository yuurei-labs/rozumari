class Logger:
    COLOR_RESET = "\033[0m"
    COLOR_SPAN = "\033[94m"
    COLOR_INFO = "\033[97m"
    COLOR_WARN = "\33[93m"
    COLOR_ERROR = "\033[91m"

    def __init__(self, span: str = "Prog") -> None:
        super().__init__()
        self.__span = span

    def info(self, msg: str) -> None:
        span_part = f"{self.COLOR_SPAN}[{self.__span}]{self.COLOR_RESET}"
        msg_part = f"{self.COLOR_INFO}{msg}{self.COLOR_RESET}"
        print(f"{span_part} {msg_part}")

    def warning(self, msg: str) -> None:
        span_part = f"{self.COLOR_SPAN}[{self.__span}]{self.COLOR_RESET}"
        msg_part = f"{self.COLOR_WARN}{msg}{self.COLOR_RESET}"
        print(f"{span_part} {msg_part}")

    def error(self, msg: str) -> None:
        span_part = f"{self.COLOR_SPAN}[{self.__span}]{self.COLOR_RESET}"
        msg_part = f"{self.COLOR_ERROR}{msg}{self.COLOR_RESET}"
        print(f"{span_part} {msg_part}")
