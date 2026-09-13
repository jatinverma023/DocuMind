"""
Shared rate limiter instance. Kept in its own module (not main.py) so
route files can import it without a circular import back to main.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Keyed by IP address — simple and works without needing to decode the JWT
# just to rate-limit. A more precise setup would key by user id instead,
# but that means running auth before rate-limiting, which slowapi doesn't
# make trivial. IP-based is the standard default and good enough here.
limiter = Limiter(key_func=get_remote_address)