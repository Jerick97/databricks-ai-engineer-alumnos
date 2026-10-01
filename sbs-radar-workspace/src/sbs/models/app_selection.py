"""Server environment selection; never accepts client request parameters."""
DEFAULT = 'config/generation-selection-073.json'
ALTERNATIVE = 'config/generation-selection-077.json'

def server_selection(environ):
    selected = environ.get('SBS_GENERATION_SELECTION', DEFAULT)
    if selected not in (DEFAULT, ALTERNATIVE):
        raise ValueError('SERVER_GENERATION_SELECTION_INVALID')
    return selected

def create_server_service(environ, *, service_factory=None, **kwargs):
    selected = server_selection(environ)
    if service_factory is None:
        from sbs.runtime import create_service
        service_factory = create_service
    service = service_factory(**kwargs)
    service.generation_selection_path = selected
    return service
