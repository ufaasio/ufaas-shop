# Event listener to prevent changes after insertion except for the fields is_default and is_active
from sqlalchemy import inspect
from sqlalchemy.orm import sessionmaker, Session
from apps.base.models import RevenueSharingRule

def prevent_changes_after_insert(mapper, connection, target):
    state = inspect(target)

    for attr in state.attrs:
        if attr.key not in ["is_default", "is_active"]:
            attr.history._immutable = True

def validate_no_changes_except_is_default_is_active(session, flush_context, instances):
    for instance in session.dirty:
        if isinstance(instance, RevenueSharingRule):
            history = inspect(instance).attrs
            for name, attr in history.items():
                if name not in ["is_default", "is_active"] and attr.history.has_changes():
                    raise ValueError(f"Column '{name}' is not editable after insertion.")

