import io
import os
import pathlib
import secrets
import sqlite3
import urllib
import urllib.request
import wave

SCRIPT_DIR = pathlib.Path(__file__).parent
DB_FILE = SCRIPT_DIR / "db.sqlite3"


def load_dotenv(filepath=SCRIPT_DIR / ".env"):
    if not filepath.exists():
        return
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip().strip('"').strip("'")


load_dotenv()

USER_HASH = os.environ["USER_HASH"]


def upload_to_catbox(filename, buf) -> str:
    # Uses form-data standard as defined at
    # https://datatracker.ietf.org/doc/html/rfc7578#autoid-4

    form_data = io.BytesIO()
    boundary = f"------{secrets.token_urlsafe(16)}"

    def add_field(name, value):
        form_data.write(f"--{boundary}\r\n".encode("utf-8"))
        form_data.write(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode("utf-8")
        )
        form_data.write(f"{value}\r\n".encode("utf-8"))

    def add_file(name, filename, type, data):
        form_data.write(f"--{boundary}\r\n".encode("utf-8"))
        form_data.write(
            f'content-disposition: form-data; name="{name}"; filename="{filename}"\r\n'.encode(
                "utf-8"
            )
        )
        form_data.write(f"content-type: {type}\r\n\r\n".encode("utf-8"))
        form_data.write(data + b"\r\n")

    add_field("reqtype", "fileupload")
    add_field("userhash", USER_HASH)
    # Catbox doesn't seem to care about the file type, so it's redundant
    add_file("fileToUpload", filename, "none", buf)

    form_data.write(f"--{boundary}--\r\n".encode("utf-8"))

    request = urllib.request.Request(
        "https://catbox.moe/user/api.php", data=form_data.getvalue()
    )
    request.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")

    resp = urllib.request.urlopen(request)
    return resp.read().decode()


def migrate(cursor: sqlite3.Cursor):
    migrations = [
        "CREATE TABLE Packs(\n"
        "  name CHARACTER VARYING(50) NOT NULL,\n"
        "  url  CHARACTER VARYING(50) NOT NULL,\n"
        "  CONSTRAINT PK_Packs_name\n"
        "    PRIMARY KEY(name)\n"
        ");",

        "ALTER TABLE Packs\n" "  ADD COLUMN kps_bytes INT NOT NULL;\n",
    ]

    res = cursor.execute("PRAGMA user_version;")
    current = res.fetchone()[0]
    print("CURRENT MIGRATION:", current)

    if current >= len(migrations):
        return

    for index, script in enumerate(migrations[current:], current + 1):
        print(f"--- MIGRATION {index} ---")
        print(script)
        cursor.execute(script)
        cursor.execute(f"PRAGMA user_version = {index}")
        print(f"--- SUCCESS ---")

    cursor.connection.commit()


def create_kps_file_for(folder: pathlib.Path) -> io.BytesIO:
    final = io.BytesIO()

    def int_to_bytes(num: int):
        return num.to_bytes(4, "little", signed=False)

    files = sorted(
        [f for f in folder.iterdir() if f.is_file() and f.suffix.lower() == ".wav"]
    )
    final.write(int_to_bytes(len(files)))

    current = 0
    wavbuf = io.BytesIO()
    wav_concat = wave.open(wavbuf, "wb")
    params_set = False

    for file in files:
        with wave.open(str(file), "rb") as wav:
            if not params_set:
                wav_concat.setparams(wav.getparams())
                params_set = True

            final.write(int_to_bytes(current))
            current += wav.getnframes()
            final.write(int_to_bytes(current))
            wav_concat.writeframes(wav.readframes(wav.getnframes()))

    wav_concat.close()
    final.write(wavbuf.getvalue())

    return final

def main():
    con = sqlite3.connect(DB_FILE)
    migrate(con.cursor())

    for folder in (SCRIPT_DIR / "sounds").iterdir():
        print(f"Working on: {folder.name}")

        kps_buf = create_kps_file_for(folder)
        buf_size = len(kps_buf.getbuffer())
        print(f"Completed generating KPS file ({buf_size} bytes)")

        res = con.execute(
            "SELECT kps_bytes FROM Packs WHERE name = ?", [folder.name]
        )
        row = res.fetchone()
        if row and row[0] == buf_size:
            print(
                f"Ignoring {folder.name} because it was already uploaded (the byte count match)"
            )
            continue

        url = upload_to_catbox(f"{folder.name}.kps", kps_buf.getvalue())
        print(f"Completed uploading the file to Catbox for URL: {url}")

        con.execute(
            "INSERT INTO packs(name, url, kps_bytes) VALUES (:name, :url, :bytes)"
            "ON CONFLICT(name) DO UPDATE SET url = :url, kps_bytes = :bytes",
            dict(name=folder.name, url=url, bytes=buf_size),
        )
        con.commit()
        print("Completed adding record to the database.")

    print("\n" + "*" * 10 + "\n")

    # ANSI escope codes for styling:
    # https://en.wikipedia.org/wiki/ANSI_escape_code#Select_Graphic_Rendition_parameters
    print("\033[1m* Update the user script with ONE of these templates:\033[0m")
    for name, url in con.execute("SELECT name, url FROM Packs").fetchall():
        print(f"\033[1;34mTemplate Name: {name}\033[0m")
        print(f"\033[1;33m// @resource    PACK {url}\033[0m")


if __name__ == "__main__":
    main()
