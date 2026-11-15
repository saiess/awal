"""Developer QA against an extracted release, using that release's Python.

Run once with --reference (an explicitly authorized local recording), then in
a fresh process with --resume. Never included in the friend distribution.
"""

import argparse
import hashlib
import io
import json
import os
import socket
import sys
import time
import zipfile
from pathlib import Path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    parser.add_argument("--reference",type=Path)
    parser.add_argument("--resume",action="store_true")
    args=parser.parse_args()
    root=args.root.resolve()
    if not (root / "MANIFEST.json").is_file() or root==Path(__file__).resolve().parents[1]:
        raise ValueError("Use a clean extracted release, never the working application.")
    sys.path.insert(0,str(root))
    os.environ["HF_HUB_OFFLINE"]="1"
    os.environ["TRANSFORMERS_OFFLINE"]="1"
    os.environ["TTS_DATA_DIR"]=str(root / "data")
    original_connect=socket.socket.connect
    def offline_connect(sock,address):
        if sock.family in (socket.AF_INET,socket.AF_INET6) and address[0] not in ("127.0.0.1","::1","localhost"):
            raise RuntimeError("Network connection attempted during offline release QA")
        return original_connect(sock,address)
    socket.socket.connect=offline_connect
    from fastapi.testclient import TestClient
    import soundfile as sf
    import app.main as application
    from app.config import Settings
    from app.projects import file_hash
    from app.tts.engine import TurboEngine
    assert Path(application.__file__).resolve().is_relative_to(root)
    engine=TurboEngine(Settings())
    engine.prepare_runtime()
    app=application.create_app(engine=engine)
    report=json.loads(args.report.read_text(encoding="utf-8")) if args.resume else {}

    def get(client,path):
        response=client.get(path)
        response.raise_for_status()
        return response.json()

    def post(client,path,payload):
        response=client.post(path,json=payload)
        response.raise_for_status()
        return response.json()

    def finish(client,job):
        deadline=time.monotonic()+600
        while time.monotonic()<deadline:
            state=get(client,"/api/jobs/"+job["id"])
            if state["status"] in ("failed","interrupted"):
                raise RuntimeError(state)
            if state["status"]=="ready":
                return state
            time.sleep(.2)
        raise RuntimeError("GPU QA job timed out")

    with TestClient(app,base_url="http://127.0.0.1") as client:
        if args.resume:
            project=get(client,"/api/projects/"+report["project_id"])
            for section in project["segments"]:
                assert file_hash(root / "data" / section["audio_path"])==report["final_raw_hashes"][section["id"]]
            recovery=get(client,"/api/projects/"+report["recovery_project_id"])
            first,second=recovery["segments"]
            assert first["status"]=="ready" and second["status"]=="pending"
            assert file_hash(root / "data" / first["audio_path"])==report["recovery_first_hash"]
            job=post(client,f"/api/projects/{recovery['id']}/generate",{})
            assert job["total_segments"]==1
            finish(client,job)
            recovery=get(client,"/api/projects/"+recovery["id"])
            assert all(s["status"]=="ready" for s in recovery["segments"])
            assert file_hash(root / "data" / recovery["segments"][0]["audio_path"])==report["recovery_first_hash"]
            report.update(status="passed",fresh_process_offline_reopen=True,shutdown_resume=True,
                          resumed_only_pending=True,completed_raw_preserved=True,external_tcp_connections_blocked=True)
        else:
            assert args.reference and args.reference.is_file()
            assert get(client,"/api/narrators")==[] and get(client,"/api/projects")==[]
            assert client.get("/").status_code==200
            import re
            script=re.search(r'src="(/static/ui/assets/[^\"]+\.js)"',client.get("/").text)
            assert script and client.get(script.group(1)).status_code==200
            assert client.get("/docs").status_code==200
            upload=client.post("/api/narrators",data=dict(label="Authorized release QA reference",rights_confirmed="true"),
                               files=dict(reference_audio=("reference.wav",args.reference.read_bytes(),"audio/wav")))
            upload.raise_for_status()
            voice=upload.json()
            text=("A quiet morning is a good time to test a new idea. We can listen carefully, make a small change, and compare the result.\n\n"
                  "This narration is generated on the computer in front of us. The saved recording stays at its original speed.\n\n"
                  "When we export a processed copy, the tempo changes while the pitch stays consistent. The original audio remains safe.")
            project=post(client,"/api/projects",dict(title="Clean release GPU check",script=text,narrator_id=voice["id"]))
            pid=project["id"]
            finish(client,post(client,f"/api/projects/{pid}/generate",{}))
            project=get(client,f"/api/projects/{pid}")
            assert len(project["segments"])==3
            before={s["id"]:file_hash(root / "data" / s["audio_path"]) for s in project["segments"]}
            middle=project["segments"][1]
            old_path=root / "data" / middle["audio_path"]
            edit=client.patch(f"/api/projects/{pid}/segments/{middle['id']}",json={"text":"This revised section is generated locally, while the surrounding recordings stay unchanged."})
            edit.raise_for_status()
            finish(client,post(client,f"/api/projects/{pid}/segments/{middle['id']}/regenerate",{}))
            project=get(client,f"/api/projects/{pid}")
            final={s["id"]:file_hash(root / "data" / s["audio_path"]) for s in project["segments"]}
            assert file_hash(old_path)==before[middle["id"]]
            assert all(final[sid]==sha for sid,sha in before.items() if sid!=middle["id"])
            assert project["segments"][1]["version"]==2
            media=client.get(f"/api/projects/{pid}/segments/{middle['id']}/audio",headers={"Range":"bytes=0-1023"})
            assert media.status_code==206 and len(media.content)==1024
            exports=[]
            for options in (dict(format="wav",processed=False),dict(format="wav",processed=True,speed=1.1),
                            dict(format="mp3",processed=True,speed=1.1),
                            dict(format="wav",processed=True,speed=1.1,include_segments=True,
                                 segment_ids=[project["segments"][0]["id"],project["segments"][-1]["id"]])):
                record=post(client,f"/api/projects/{pid}/exports",options)
                download=client.get(f"/api/projects/{pid}/exports/{record['id']}/download")
                download.raise_for_status()
                assert hashlib.sha256(download.content).hexdigest()==record["sha256"]
                if options.get("include_segments"):
                    with zipfile.ZipFile(io.BytesIO(download.content)) as archive:
                        assert len(archive.namelist())==4 and "sections.json" in archive.namelist()
                else:
                    info=sf.info(io.BytesIO(download.content))
                    assert info.duration>0 and info.samplerate==24000
                exports.append(dict(format=options["format"],zip=options.get("include_segments",False),
                                    effective_speed=record["effective_speed"],duration_seconds=record["duration_seconds"]))
            assert all(file_hash(root / "data" / s["audio_path"])==final[s["id"]] for s in project["segments"])
            recovery=post(client,"/api/projects",dict(title="Release shutdown recovery",narrator_id=voice["id"],
                script="The current section should finish safely before this application closes.\n\nOnly the unfinished section should be generated when we reopen the application."))
            post(client,f"/api/projects/{recovery['id']}/generate",{})
            deadline=time.monotonic()+60
            while time.monotonic()<deadline:
                state=get(client,"/api/projects/"+recovery["id"])
                if state["segments"][0]["status"]=="generating":
                    break
                time.sleep(.01)
            else:
                raise RuntimeError("Recovery test did not enter active generation")
            report.update(status="awaiting_fresh_process_resume",empty_initial_workspace=True,
                          authorized_reference_upload=True,real_cuda_generation=True,sections=3,
                          single_section_regeneration=True,old_and_unrelated_raws_preserved=True,
                          media_range=True,exports=exports,project_id=pid,final_raw_hashes=final,
                          recovery_project_id=recovery["id"],model_weights_bundled=False)
    if not args.resume:
        recovery=app.state.store.read(report["recovery_project_id"])
        assert recovery["segments"][0]["status"]=="ready" and recovery["segments"][1]["status"]=="pending"
        report["recovery_first_hash"]=file_hash(root / "data" / recovery["segments"][0]["audio_path"])
    args.report.write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))


if __name__=="__main__":
    main()
