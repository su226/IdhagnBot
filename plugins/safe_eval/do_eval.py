import json
import resource
import sys

data = json.loads(sys.stdin.buffer.read())
resource.setrlimit(resource.RLIMIT_NPROC, (data["nproc"], data["nproc"]))
resource.setrlimit(resource.RLIMIT_AS, (data["memory"], data["memory"]))
exec(data["code"], {}, {})
