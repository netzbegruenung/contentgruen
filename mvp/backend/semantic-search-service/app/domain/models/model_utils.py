import datetime
import uuid


class ModelValidator:

    @staticmethod
    def validate_uuid(value):
        if isinstance(value, uuid.UUID):
            # If the value is already a UUID object, return it directly
            return value
        elif isinstance(value, str):
            try:
                # If the value is a string, attempt to convert it to a UUID object
                return uuid.UUID(value)
            except ValueError as e:
                raise ValueError(f"Invalid UUID format: {value}. Error: {e}")
        else:
            # If the value is neither a string nor a UUID object, raise an error
            raise TypeError(
                f"Expected a UUID object or a string, but got {type(value)} instead."
            )

    @staticmethod
    def validate_datetime(value):
        if isinstance(value, datetime.datetime):
            # If the value is already a datetime object, return it directly
            return value
        elif isinstance(value, str):
            try:
                # If the value is a string, attempt to convert it to a datetime object
                return datetime.datetime.fromisoformat(value)
            except ValueError as e:
                raise ValueError(
                    f"Invalid datetime format for {value}. Expected isoformat. Error: {e}"
                )
        else:
            # If the value is neither a string nor a datetime object, raise an error
            raise TypeError(
                f"Expected a datetime object or a string, but got {type(value)} instead."
            )
