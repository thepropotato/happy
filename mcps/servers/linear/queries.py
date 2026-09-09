"""THE GRAPHQL LINEAR IS ASKED, KEPT AWAY FROM THE TOOLS THAT ASK IT.

EVERY FIELD AND EVERY ARGUMENT HERE WAS READ OFF LINEAR'S OWN SCHEMA BY INTROSPECTION RATHER
THAN OUT OF A DOCUMENT, BECAUSE THE TWO DISAGREE: THE MUTATIONS ARE Retire AND Restore AND
NOT Archive, AND A MILESTONE IS A projectMilestone WITH NO milestones QUERY AT ALL."""

# ── WHAT EACH KIND OF THING IS WORTH SAYING ──

# NOT THE DESCRIPTION: IT IS AN ESSAY ON HALF THE ISSUES AND THE ONE TOOL THAT WANTS IT ASKS
# FOR IT BY ITSELF.
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
  parent { identifier title }
  children { nodes { identifier title } }
"""
)

LABEL = "id name description color isGroup retiredAt team { key } parent { name }"

PERSON = "id name displayName email active guest title timezone"

TEAM = "id key name description cyclesEnabled"

PROJECT = """
  id
  name
  description
  slugId
  url
  progress
  startDate
  targetDate
  status { name type }
  lead { name }
  teams { nodes { key } }
"""

CYCLE = """
  id number name description startsAt endsAt progress isActive isFuture isPast
  team { key name }
"""

INITIATIVE = """
  id name description slugId color icon status targetDate url
  owner { name }
  leadTeam { key }
"""

DOCUMENT = """
  id title summary slugId url icon color createdAt updatedAt
  creator { name }
  project { name }
  initiative { name }
"""

MILESTONE = "id name description targetDate progress status sortOrder project { name }"

STATE = "id name type color position description team { key }"

STATUS_UPDATE = """
  id body health createdAt updatedAt url isStale
  user { name }
  project { name }
"""

RELEASE = """
  id name description version commitSha slugId url
  startDate targetDate startedAt completedAt
  stage { name }
  pipeline { name }
  creator { name }
"""

RELEASE_NOTE = """
  id title slugId url releaseCount generationStatus createdAt
  pipeline { name }
"""

PIPELINE = "id name description"

TEMPLATE = "id name description type icon color updatedAt team { key }"

SKILL = "id title description icon color slugId lastUsedAt recentUsageCount owner { name }"

ATTACHMENT = """
  id title subtitle url source sourceType createdAt
  creator { name }
  issue { identifier }
"""

NOTIFICATION = """
  id type title subtitle url readAt createdAt snoozedUntilAt category
  actor { name }
"""

COMMENT = "id body createdAt url user { name }"


# ── A LIST AND A ONE, WRITTEN ONCE PER KIND ──


def listing(query, shape, extra=""):
    """ONE PAGE OF SOMETHING. EVERY LIST QUERY IN LINEAR TAKES first AND filter THE SAME WAY."""
    return f"""
query List($filter: {extra or "JSONObject"}, $first: Int!) {{
  {query}(filter: $filter, first: $first) {{
    nodes {{ {shape} }}
  }}
}}
"""


def plain(query, shape):
    """A LIST THAT TAKES NO FILTER — templates AND organization ARE THE TWO."""
    return f"""
query List($first: Int!) {{
  {query}(first: $first) {{ nodes {{ {shape} }} }}
}}
"""


def single(query, shape):
    return f"""
query One($id: String!) {{
  {query}(id: $id) {{ {shape} }}
}}
"""


def creating(mutation, kind, shape):
    return f"""
mutation Make($input: {kind}!) {{
  {mutation}(input: $input) {{ success {noun(mutation)} {{ {shape} }} }}
}}
"""


def updating(mutation, kind, shape):
    return f"""
mutation Change($id: String!, $input: {kind}!) {{
  {mutation}(id: $id, input: $input) {{ success {noun(mutation)} {{ {shape} }} }}
}}
"""


def switching(mutation):
    """RETIRE, RESTORE AND DELETE ALL TAKE AN ID AND ANSWER WITH success AND NOTHING ELSE."""
    return f"""
mutation Switch($id: String!) {{
  {mutation}(id: $id) {{ success }}
}}
"""


def noun(mutation):
    """WHAT A PAYLOAD CALLS THE THING IT MADE, WHICH IS THE MUTATION WITHOUT ITS VERB."""
    for verb in ("Create", "Update", "Retire", "Restore", "Delete", "Archive"):
        if mutation.endswith(verb):
            return mutation[: -len(verb)]

    return mutation


# ── ISSUES ──

ISSUES = f"""
query Issues($filter: IssueFilter, $first: Int!) {{
  issues(filter: $filter, first: $first, orderBy: updatedAt) {{ nodes {{ {BRIEF} }} }}
}}
"""

ONE_ISSUE = single("issue", WHOLE)

SEARCH = f"""
query Search($term: String!, $first: Int!) {{
  searchIssues(term: $term, first: $first) {{ nodes {{ {BRIEF} }} }}
}}
"""

NEW_ISSUE = creating("issueCreate", "IssueCreateInput", BRIEF)

CHANGE_ISSUE = updating("issueUpdate", "IssueUpdateInput", BRIEF)

# SHARING IS WITH ONE PERSON AT A TIME, NOT A LINK: BOTH TAKE WHO AS WELL AS WHICH.
SHARE_ISSUE = """
mutation Share($id: String!, $userId: String!) {
  issueShare(id: $id, userId: $userId) { success }
}
"""

UNSHARE_ISSUE = """
mutation Unshare($id: String!, $userId: String!) {
  issueUnshare(id: $id, userId: $userId) { success }
}
"""

# ── COMMENTS ──

COMMENTS = f"""
query Comments($id: String!, $first: Int!) {{
  issue(id: $id) {{
    identifier
    comments(first: $first) {{ nodes {{ {COMMENT} }} }}
  }}
}}
"""

NEW_COMMENT = creating("commentCreate", "CommentCreateInput", COMMENT)

DROP_COMMENT = switching("commentDelete")

# ── STATES ──

STATES = listing("workflowStates", STATE, "WorkflowStateFilter")

ONE_STATE = single("workflowState", STATE)

# ── PEOPLE AND PLACES ──

TEAMS = listing("teams", TEAM, "TeamFilter")

ONE_TEAM = single("team", TEAM + " states(first: 50) { nodes { id name type } }")

PEOPLE = listing("users", PERSON, "UserFilter")

ONE_PERSON = single("user", PERSON)

ME = """
query Me {
  viewer { id name email }
  organization { id name urlKey userCount }
}
"""

WORKSPACE = """
query Workspace {
  organization {
    id name urlKey userCount createdAt
    teams(first: 50) { nodes { key name } }
  }
}
"""

# ── PROJECTS, CYCLES, MILESTONES ──

PROJECTS = f"""
query Projects($filter: ProjectFilter, $first: Int!) {{
  projects(filter: $filter, first: $first, orderBy: updatedAt) {{ nodes {{ {PROJECT} }} }}
}}
"""

ONE_PROJECT = single("project", PROJECT)

NEW_PROJECT = creating("projectCreate", "ProjectCreateInput", PROJECT)

CHANGE_PROJECT = updating("projectUpdate", "ProjectUpdateInput", PROJECT)

CYCLES = listing("cycles", CYCLE, "CycleFilter")

MILESTONES = listing("projectMilestones", MILESTONE, "ProjectMilestoneFilter")

ONE_MILESTONE = single("projectMilestone", MILESTONE)

NEW_MILESTONE = creating("projectMilestoneCreate", "ProjectMilestoneCreateInput", MILESTONE)

CHANGE_MILESTONE = updating("projectMilestoneUpdate", "ProjectMilestoneUpdateInput", MILESTONE)

# ── LABELS: THE SAME FIVE THINGS, THREE TIMES OVER ──

ISSUE_LABELS = listing("issueLabels", LABEL, "IssueLabelFilter")

NEW_ISSUE_LABEL = creating("issueLabelCreate", "IssueLabelCreateInput", LABEL)

CHANGE_ISSUE_LABEL = updating("issueLabelUpdate", "IssueLabelUpdateInput", LABEL)

RETIRE_ISSUE_LABEL = switching("issueLabelRetire")

RESTORE_ISSUE_LABEL = switching("issueLabelRestore")

PROJECT_LABELS = listing("projectLabels", LABEL, "ProjectLabelFilter")

NEW_PROJECT_LABEL = creating("projectLabelCreate", "ProjectLabelCreateInput", LABEL)

RETIRE_PROJECT_LABEL = switching("projectLabelRetire")

RESTORE_PROJECT_LABEL = switching("projectLabelRestore")

INITIATIVE_LABELS = listing("initiativeLabels", LABEL, "InitiativeLabelFilter")

NEW_INITIATIVE_LABEL = creating("initiativeLabelCreate", "InitiativeLabelCreateInput", LABEL)

CHANGE_INITIATIVE_LABEL = updating("initiativeLabelUpdate", "InitiativeLabelUpdateInput", LABEL)

RETIRE_INITIATIVE_LABEL = switching("initiativeLabelRetire")

RESTORE_INITIATIVE_LABEL = switching("initiativeLabelRestore")

# ── INITIATIVES ──

INITIATIVES = listing("initiatives", INITIATIVE, "InitiativeFilter")

ONE_INITIATIVE = single("initiative", INITIATIVE)

NEW_INITIATIVE = creating("initiativeCreate", "InitiativeCreateInput", INITIATIVE)

CHANGE_INITIATIVE = updating("initiativeUpdate", "InitiativeUpdateInput", INITIATIVE)

# ── DOCUMENTS ──

DOCUMENTS = listing("documents", DOCUMENT, "DocumentFilter")

ONE_DOCUMENT = single("document", DOCUMENT + " content")

NEW_DOCUMENT = creating("documentCreate", "DocumentCreateInput", DOCUMENT)

CHANGE_DOCUMENT = updating("documentUpdate", "DocumentUpdateInput", DOCUMENT)

# ── STATUS UPDATES ──

STATUS_UPDATES = listing("projectUpdates", STATUS_UPDATE, "ProjectUpdateFilter")

NEW_STATUS_UPDATE = creating("projectUpdateCreate", "ProjectUpdateCreateInput", STATUS_UPDATE)

DROP_STATUS_UPDATE = switching("projectUpdateArchive")

# ── RELEASES ──

RELEASES = listing("releases", RELEASE, "ReleaseFilter")

ONE_RELEASE = single("release", RELEASE)

NEW_RELEASE = creating("releaseCreate", "ReleaseCreateInput", RELEASE)

CHANGE_RELEASE = updating("releaseUpdate", "ReleaseUpdateInput", RELEASE)

RELEASE_NOTES = listing("releaseNotes", RELEASE_NOTE, "ReleaseNoteFilter")

ONE_RELEASE_NOTE = single("releaseNote", RELEASE_NOTE)

NEW_RELEASE_NOTE = creating("releaseNoteCreate", "ReleaseNoteCreateInput", RELEASE_NOTE)

CHANGE_RELEASE_NOTE = updating("releaseNoteUpdate", "ReleaseNoteUpdateInput", RELEASE_NOTE)

PIPELINES = listing("releasePipelines", PIPELINE, "ReleasePipelineFilter")

# ── TEMPLATES AND SKILLS ──

TEMPLATES = plain("templates", TEMPLATE)

ONE_TEMPLATE = single("template", TEMPLATE + " templateData")

SKILLS = listing("agentSkills", SKILL, "AgentSkillFilter")

ONE_SKILL = single("agentSkill", SKILL + " body")

# ── ATTACHMENTS ──

ONE_ATTACHMENT = single("attachment", ATTACHMENT)

NEW_ATTACHMENT = creating("attachmentCreate", "AttachmentCreateInput", ATTACHMENT)

DROP_ATTACHMENT = switching("attachmentDelete")

# WHAT A FILE UPLOAD BEGINS WITH: LINEAR SIGNS A URL AND THE FILE ITSELF GOES STRAIGHT TO IT.
UPLOAD = """
mutation Upload($contentType: String!, $filename: String!, $size: Int!) {
  fileUpload(contentType: $contentType, filename: $filename, size: $size) {
    success
    uploadFile {
      uploadUrl
      assetUrl
      contentType
      filename
      size
      headers { key value }
    }
  }
}
"""

# ── DIFFS ──

# THE ONLY ONE OF LINEAR'S SEVEN CODE REVIEW TOOLS THE PUBLIC API CAN DO: THERE IS A diff(id)
# QUERY AND NO diffs LIST, NO THREADS AND NO MUTATIONS AT ALL. THE REST RUN ON THE AGENT
# SESSION PROTOCOL, WHICH IS NOT THE GRAPHQL API.
ONE_DIFF = """
query Diff($id: String!) {
  diff(id: $id) {
    id
    fileCount
    additions
    deletions
    truncated
    createdAt
    pullRequest { url }
    creator { name }
    files { path oldPath state additions deletions }
  }
}
"""

# ── NOTIFICATIONS ──

NOTIFICATIONS = listing("notifications", NOTIFICATION, "NotificationFilter")

MARK_NOTIFICATION = """
mutation Mark($id: String!, $input: NotificationUpdateInput!) {
  notificationUpdate(id: $id, input: $input) { success }
}
"""
