class NoSuchParameterException(Exception):
    pass


class AmbiguousDependencyException(Exception):
    pass


class InvalidInjectionConfigurationError(Exception):
    pass


InvalidInjectionConfigurationException = InvalidInjectionConfigurationError
