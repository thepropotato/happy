"""GOOGLE DRIVE: FINDING A FILE, READING ONE, MAKING ONE, AND SHARING IT."""

import io

from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload

from servers.google import account, mcp
from servers.shared.answering import ok, some

FIELDS = "files(id, name, mimeType, modifiedTime, size, webViewLink)"

# WHAT A GOOGLE DOC HAS TO BE TURNED INTO BEFORE IT IS TEXT AT ALL.
AS_TEXT = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
    "application/vnd.google-apps.presentation": "text/plain",
}

MOST_BODY = 4000


@mcp.tool()
def search_files(query: str = "", limit: int = 10) -> str:
    """Find files in Drive by name, most recently changed first.

    The query is matched against the file name. Reading one needs read_file and
    the id this gives back.
    """
    asked = "trashed = false"

    if query:
        asked += f" and name contains '{query.replace(chr(39), '')}'"

    found = (
        account.drive()
        .files()
        .list(
            q=asked,
            orderBy="modifiedTime desc",
            pageSize=max(1, min(int(limit), 25)),
            fields=FIELDS,
        )
        .execute()
    )

    return ok([outlined(each) for each in found.get("files", [])])


@mcp.tool()
def read_file(file_id: str) -> str:
    """Read what is in a Drive file, given the id search_files gave back.

    Google Docs and Sheets are turned into plain text on the way out. A file that
    is not text at all, like a picture, comes back as a description rather than
    its contents.
    """
    service = account.drive()
    about = service.files().get(fileId=file_id, fields="id, name, mimeType").execute()
    kind = about.get("mimeType", "")

    if kind in AS_TEXT:
        asked = service.files().export_media(fileId=file_id, mimeType=AS_TEXT[kind])
    elif kind.startswith("text/") or kind == "application/json":
        asked = service.files().get_media(fileId=file_id)
    else:
        return ok({"id": file_id, "name": about.get("name"), "kind": kind, "body": ""})

    return ok(
        {
            "id": file_id,
            "name": about.get("name"),
            "kind": kind,
            "body": pulled(asked)[:MOST_BODY],
        }
    )


@mcp.tool()
def create_file(name: str, content: str, folder_id: str = "") -> str:
    """Make a new text file in Drive. Left without a folder it lands in My Drive."""
    about = {"name": name}

    if folder_id:
        about["parents"] = [folder_id]

    carrying = MediaIoBaseUpload(
        io.BytesIO(content.encode("utf-8")), mimetype="text/plain", resumable=False
    )
    made = (
        account.drive()
        .files()
        .create(body=about, media_body=carrying, fields="id, name, webViewLink")
        .execute()
    )

    return ok({"created": True, "id": made.get("id"), "name": made.get("name"),
               "link": made.get("webViewLink")})


@mcp.tool()
def share_file(file_id: str, email: str, role: str = "reader") -> str:
    """Give somebody access to a file. role is reader, commenter or writer.

    This hands a real person real access, so say whose file and whose address
    before calling it.
    """
    account.drive().permissions().create(
        fileId=file_id,
        body={"type": "user", "role": role or "reader", "emailAddress": email},
        sendNotificationEmail=True,
    ).execute()

    return ok({"shared": True, "id": file_id, "with": email, "role": role or "reader"})


def outlined(file):
    return {
        "id": file.get("id"),
        "name": some(file.get("name", ""), 160),
        "kind": file.get("mimeType", "").rsplit(".", 1)[-1],
        "changed": file.get("modifiedTime"),
        "link": file.get("webViewLink"),
    }


def pulled(asked):
    held = io.BytesIO()
    puller = MediaIoBaseDownload(held, asked)
    done = False

    while not done:
        done = puller.next_chunk()[1]

    return held.getvalue().decode("utf-8", "replace")
