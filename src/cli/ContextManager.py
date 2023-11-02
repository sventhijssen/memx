from core.BooleanFunctionCollection import BooleanFunctionCollection


class ContextManager:

    def __init__(self):
        """
        The context manager keeps record of the Boolean function(s).
        These Boolean functions can be transformed through commands.
        TODO: In future versions, we will remove the dictionary, and we will only keep record of the current state.
        """

        self.current_context = None
        self.contexts = dict()

    def get_context(self, name: str = None) -> BooleanFunctionCollection:
        if not name:
            return self.contexts[self.current_context]
        return self.contexts[name]

    def add_context(self, name: str, benchmark: BooleanFunctionCollection):
        self.contexts[name] = benchmark
        self.current_context = name
