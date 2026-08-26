"""THE PART THAT KEEPS TIME ON ITS OWN, AND SAYS SO WHEN SOMETHING COMES ROUND."""

from heart.beating import start, stop
from heart.resolving import moment
from heart.wording import away, briefly, repeatedly, spoken

__all__ = ["away", "briefly", "moment", "repeatedly", "spoken", "start", "stop"]
