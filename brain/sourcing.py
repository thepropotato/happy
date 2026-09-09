"""WHETHER THE VALUES IN A TOOL CALL CAME FROM A TOOL, OR THE MODEL WROTE THEM ITSELF.

ONE CHECK FOR EVERY TOOL, OURS AND EVERY CONNECTOR'S, ASKED AT THE ONE POINT BOTH LOOPS
PUT A CALL THROUGH. A GUARD WRITTEN FOR ONE TOOL CATCHES ONE TOOL; THIS ASKS THE SAME
QUESTION OF ANY ARGUMENT THAT NAMES SOMETHING IN THE WORLD, SO A CONNECTOR ADDED TOMORROW
IS COVERED WITHOUT A LINE BEING WRITTEN FOR IT.

A PATH IS THE FIRST KIND. AN ADDRESS ALREADY HAS ITS OWN IN hands/web/handed.py, CALLED
FROM THE TOOLS THEMSELVES BECAUSE THOSE TOOLS ARE OURS AND RUN IN THIS PROCESS. A
CONNECTOR'S TOOLS DO NOT: THEY ARE A SUBPROCESS OVER STDIO AND CANNOT SEE WHAT THIS ONE
WAS HANDED, WHICH IS WHY THE ASKING HAPPENS HERE AND NOT INSIDE THE SERVER."""

from hands.files import held

# AN ARGUMENT WHOSE NAME SAYS IT CARRIES A PATH. THE MODEL PICKS THE NAME FROM THE SCHEMA,
# SO THESE ARE THE WORDS CONNECTORS ACTUALLY USE FOR "THE FILE TO ACT ON".
PATHED = ("source", "path", "file", "filename", "file_path", "filepath", "attachment", "media")

# ARGUMENTS THAT NAME A PATH BUT ARE WHERE SOMETHING IS *GOING*, NOT WHAT IS BEING ACTED ON.
# A FILE ABOUT TO BE WRITTEN CANNOT HAVE BEEN HANDED OVER, BECAUSE IT DOES NOT EXIST YET.
WRITING = ("write_file", "edit_file", "write_document", "download", "download_images",
           "screenshot", "build", "restore_from_trash")

# THE TOOLS WHOSE PATH ARGUMENT IS LOOKED UP BEFORE IT IS USED. locate() TAKES A BARE NAME
# OR A DESCRIPTION AND GOES AND FINDS IT, WHICH IS THE LOOKING THIS GUARD EXISTS TO FORCE,
# SO ASKING FOR PROVENANCE FIRST WOULD ONLY FORBID THE RIGHT BEHAVIOUR.
LOOKING = ("read_file", "find_files", "list_folder", "move_to_trash", "open_path", "describe_project")


def checked(name, args):
    """THE WORDS TO TURN THIS CALL BACK WITH, OR None IF EVERY VALUE IN IT WAS HANDED OVER."""
    if not isinstance(args, dict) or wrote(name):
        return None

    for key, value in args.items():
        if key.lower() not in PATHED:
            continue

        for said in spread(value):
            _, refusal = held.resolve(said)

            if refusal:
                return refusal

    return None


def wrote(name):
    """A TOOL THAT MAKES THE FILE IT NAMES, OR LOOKS THE NAME UP ITSELF."""
    plain = str(name or "").lower()

    return any(plain.endswith(each) or plain == each for each in WRITING + LOOKING)


def spread(value):
    """ONE PATH, OR EVERY PATH IN A LIST OF THEM."""
    if isinstance(value, str):
        return [value] if value.strip() else []

    if isinstance(value, (list, tuple)):
        return [each for each in value if isinstance(each, str) and each.strip()]

    return []
