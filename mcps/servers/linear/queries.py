"""THE GRAPHQL LINEAR IS ASKED, KEPT AWAY FROM THE TOOLS THAT ASK IT."""

# WHAT AN ISSUE IS WORTH SAYING OUT LOUD. NOT THE DESCRIPTION: IT IS AN ESSAY ON
# HALF THE ISSUES AND THE ONE TOOL THAT WANTS IT ASKS FOR IT BY ITSELF.
BRIEF = """
  id
  identifier
  title
  priority
  url
  state { name type }
  assignee { name }
  team { key }
"""

WHOLE = (
    BRIEF
    + """
  description
  createdAt
  updatedAt
  dueDate
  estimate
  labels { nodes { name } }
  project { name }
  cycle { number name }
"""
)

# ONE PAGE OF ISSUES, NARROWED BY WHATEVER THE CALLER CARES ABOUT. EVERY filter IS
# OPTIONAL AND LINEAR IGNORES THE ONES THAT ARE NULL.
ISSUES = (
    """
query Issues($filter: IssueFilter, $first: Int!) {
  issues(filter: $filter, first: $first, orderBy: updatedAt) {
    nodes {"""
    + BRIEF
    + """}
  }
}
"""
)

ONE_ISSUE = (
    """
query Issue($id: String!) {
  issue(id: $id) {"""
    + WHOLE
    + """}
}
"""
)

# LINEAR HAS NO SEPARATE SEARCH ENDPOINT FOR THE REST: THIS IS THE ONE THING IT
# FULL-TEXT SEARCHES, AND IT SEARCHES TITLE AND DESCRIPTION BOTH.
SEARCH = (
    """
query Search($term: String!, $first: Int!) {
  searchIssues(term: $term, first: $first) {
    nodes {"""
    + BRIEF
    + """}
  }
}
"""
)

COMMENTS = """
query Comments($id: String!, $first: Int!) {
  issue(id: $id) {
    identifier
    comments(first: $first) {
      nodes { body createdAt user { name } }
    }
  }
}
"""

TEAMS = """
query Teams($first: Int!) {
  teams(first: $first) {
    nodes { id key name description }
  }
}
"""

PROJECTS = """
query Projects($first: Int!) {
  projects(first: $first, orderBy: updatedAt) {
    nodes {
      id
      name
      state
      progress
      targetDate
      lead { name }
      teams { nodes { key } }
    }
  }
}
"""

# THE CYCLE A TEAM IS IN NOW, WHICH IS THE ONLY ONE ANYBODY ASKS ABOUT BY VOICE.
CYCLES = """
query Cycles($first: Int!) {
  cycles(first: $first, filter: { isActive: { eq: true } }) {
    nodes {
      id
      number
      name
      startsAt
      endsAt
      progress
      team { key name }
    }
  }
}
"""

ME = """
query Me {
  viewer { id name email }
  organization { name urlKey }
}
"""

# THE STATES ONE TEAM HAS, WHICH ARE THE ONLY WORDS move_issue WILL ACCEPT.
STATES = """
query States($team: String!) {
  team(id: $team) {
    key
    states(first: 50) { nodes { id name type } }
  }
}
"""

NEW_ISSUE = (
    """
mutation NewIssue($input: IssueCreateInput!) {
  issueCreate(input: $input) {
    success
    issue {"""
    + BRIEF
    + """}
  }
}
"""
)

MOVE_ISSUE = (
    """
mutation MoveIssue($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) {
    success
    issue {"""
    + BRIEF
    + """}
  }
}
"""
)

NEW_COMMENT = """
mutation NewComment($input: CommentCreateInput!) {
  commentCreate(input: $input) {
    success
    comment { id createdAt }
  }
}
"""
