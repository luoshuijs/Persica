class BrokenNonFrameworkBoundary(Exception):
    pass


raise RuntimeError("non-framework external base module should not be imported")
