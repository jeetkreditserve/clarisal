"""
Organisation audit logging is intentionally handled in services.py.

Mutations such as lifecycle transitions, licence changes, admin assignment, and
address updates already emit audit events at the service layer where request
context and payload details are available.
"""
