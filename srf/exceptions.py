from sanic.exceptions import HTTPException


class TargetObjectAlreadyExist(HTTPException):
    """
    When inserting data into the database, it already exists. You need to check the fields
    """

    status_code = 409
    quiet = True


class ImproperlyConfigured(HTTPException):
    """
    The system is improperly configured. Check your settings.
    """

    status_code = 500
