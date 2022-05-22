import pickle
import resource
import sys

data = pickle.loads(sys.stdin.buffer.read())
resource.setrlimit(resource.RLIMIT_NPROC, (data["nproc"], data["nproc"]))
resource.setrlimit(resource.RLIMIT_AS, (data["memory"], data["memory"]))
exec(data["code"], {}, {})
