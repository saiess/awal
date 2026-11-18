"""Real Chrome + CUDA parity check for the React migration; isolated local data."""

import hashlib
import io
import json
import os
import time
import zipfile
import argparse
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "test-results/react-migration" / uuid4().hex[:10]

import httpx
import numpy as np
import soundfile as sf
from playwright.sync_api import sync_playwright, expect
sys.path.insert(0,str(ROOT / "tests"))
from browser_support import start, stop, BASE


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference",type=Path,required=True,help="Authorized 10-30-second reference WAV")
    parser.add_argument("--transcript-file",type=Path,required=True,help="Confirmed exact reference transcript")
    args=parser.parse_args()
    reference=args.reference.resolve()
    transcript=args.transcript_file.read_text(encoding="utf-8").strip()
    if not transcript:
        raise ValueError("Reference transcript is required.")
    if not reference.is_file():
        raise ValueError("Provide an existing authorized reference recording.")
    RUN.mkdir(parents=True)
    os.environ["TTS_DATA_DIR"] = str(RUN / "data")
    process = None
    errors, external, mutations = [], [], []
    report = {"status": "running", "data_isolated": True}
    with (RUN / "server.log").open("w", encoding="utf-8") as log:
        try:
            process, health = start(log)
            assert health["gpu_available"] and not health["engine_loaded"]
            with sync_playwright() as pw, httpx.Client(base_url=BASE, timeout=90) as client:
                browser = pw.chromium.launch(channel="chrome", headless=True, args=["--autoplay-policy=no-user-gesture-required"])
                context = browser.new_context(viewport={"width":1440,"height":1050},accept_downloads=True)
                def route(request_route):
                    request = request_route.request
                    if request.url.startswith(BASE + "/"):
                        if request.method not in ("GET", "HEAD"): mutations.append((request.method, request.url))
                        request_route.continue_()
                    else:
                        external.append(request.url)
                        request_route.abort()
                context.route("**/*",route)
                page = context.new_page()
                page.on("pageerror",lambda error:errors.append(str(error)))
                dismiss = {"next":False}
                def dialog(value):
                    if dismiss["next"]:
                        dismiss["next"] = False
                        value.dismiss()
                    else: value.accept()
                page.on("dialog",dialog)
                page.goto(BASE)
                expect(page.locator("#voice-label")).to_have_text("Add your narrator")
                expect(page.locator("#generate")).to_be_disabled()
                assert client.get("/api/projects").json() == []
                assert page.locator('script[type="module"]').count()==1
                page.locator("#voice-settings summary").click()
                page.locator("#reference-label").fill("React QA narrator")
                page.locator("#reference-file").set_input_files(reference)
                page.locator("#reference-transcript").fill(transcript)
                page.locator("#reference-rights").check()
                page.locator('#reference-form button[type="submit"]').click()
                expect(page.locator("#voice-label")).to_have_text("React QA narrator",timeout=30_000)
                expect(page.locator("#voice-settings")).not_to_have_attribute("open","")
                page.locator("#generate").click()
                expect(page.locator("#error")).to_contain_text("Give this project a title.")
                text = ("A quiet morning is a good time to try a new idea. We can listen carefully and compare the results.\n\n"
                        "This speech is generated locally. Editing one section should preserve every unrelated recording.\n\n"
                        "The final export can change the tempo while keeping the original audio safely stored.")
                page.locator("#title").fill("React narration workflow")
                page.locator("#script").fill(text)
                page.locator("#preview-script").click()
                expect(page.locator(".section-card")).to_have_count(3)
                expect(page.locator(".section-card textarea").first).to_have_attribute("readonly","")
                dismiss["next"] = True
                page.locator("#generate").click()
                expect(page.locator("#generate")).to_be_enabled()
                assert client.get("/api/projects").json()==[]
                page.locator("#generate").click()
                expect(page.locator("#progress-panel")).to_be_visible(timeout=20_000)
                expect(page.locator("#generate")).to_be_disabled()
                page.reload()
                expect(page.locator("#progress-panel")).to_be_visible(timeout=20_000)
                expect(page.locator("#progress-label")).to_have_text("Narration saved.",timeout=600_000)
                expect(page.locator("#generate")).to_be_enabled()
                expect(page.locator("#error")).to_be_hidden()
                pid = page.evaluate("localStorage.getItem('narration-project')")
                def project(): return client.get(f"/api/projects/{pid}").json()
                def hashes(value):
                    return {s["id"]:hashlib.sha256((RUN / "data" / s["audio_path"]).read_bytes()).hexdigest() for s in value["segments"]}
                saved = project()
                assert len(saved["segments"])==3 and all(s["status"]=="ready" for s in saved["segments"])
                assert sum(url.endswith(f"/projects/{pid}/generate") for method,url in mutations if method=="POST")==1
                before = hashes(saved)
                old_middle = RUN / "data" / saved["segments"][1]["audio_path"]
                first = page.locator(".section-card").nth(0)
                middle = page.locator(".section-card").nth(1)
                first.locator("textarea").fill("Unsaved draft must survive polling and unrelated regeneration.")
                middle.locator("textarea").fill("This section has been revised. The surrounding recordings and unsaved edits should remain intact.")
                first.locator("audio").evaluate("audio => audio.play()")
                middle.locator(".regenerate-section").click()
                expect(page.locator("#generate")).to_be_disabled()
                page.wait_for_timeout(2200)
                assert first.locator("audio").evaluate("audio => audio.currentTime")>1
                expect(first.locator("textarea")).to_have_value("Unsaved draft must survive polling and unrelated regeneration.")
                expect(page.locator("#progress-label")).to_have_text("Narration saved.",timeout=180_000)
                expect(page.locator("#generate")).to_be_enabled()
                first.locator("audio").evaluate("audio => audio.pause()")
                updated = project()
                assert updated["segments"][1]["version"]==2
                assert hashlib.sha256(old_middle.read_bytes()).hexdigest()==before[saved["segments"][1]["id"]]
                assert all(hashes(updated)[sid]==value for sid,value in before.items() if sid!=saved["segments"][1]["id"])
                page.locator("#export-wav").click()
                expect(page.locator("#error")).to_contain_text("Save section text")
                dismiss["next"] = True
                page.locator("#new-project").click()
                expect(page.locator("#heading")).to_have_text("React narration workflow")
                expect(first.locator("textarea")).to_have_value("Unsaved draft must survive polling and unrelated regeneration.")
                page.locator("#new-project").click()
                expect(page.locator("#title")).to_have_value("")
                page.locator(f'#projects button[data-project-id="{pid}"]').click()
                expect(page.locator("#title")).to_have_value("React narration workflow")
                expect(page.locator("#speed")).to_have_value("1.10")
                before_exports = hashes(project())
                page.locator("#preview-master").click()
                expect(page.locator("#master-panel")).to_be_visible(timeout=30_000)
                expect(page.locator("#preview-master")).to_be_enabled()
                exports = []
                for button,format in (("#export-wav","wav"),("#export-mp3","mp3")):
                    with page.expect_download(timeout=90_000) as download:
                        page.locator(button).click()
                    payload = Path(download.value.path()).read_bytes()
                    samples,sr = sf.read(io.BytesIO(payload),dtype="float32")
                    record = project()["exports"][-1]
                    assert sr==24000 and np.isfinite(samples).all() and record["effective_speed"]==1.1
                    assert hashlib.sha256(payload).hexdigest()==record["sha256"]
                    exports.append({"format":format,"effective_speed":1.1,"seconds":record["duration_seconds"]})
                    expect(page.locator(button)).to_be_enabled(timeout=30_000)
                page.locator("#select-all").uncheck()
                page.locator(".section-select").first.check()
                page.locator(".section-select").last.check()
                with page.expect_download(timeout=90_000) as download:
                    page.locator("#export-segments").click()
                with zipfile.ZipFile(download.value.path()) as archive:
                    assert len(archive.namelist())==4
                    details=json.loads(archive.read("sections.json"))
                    assert [s["id"] for s in details["sections"]]==[saved["segments"][0]["id"],saved["segments"][-1]["id"]]
                expect(page.locator("#processed")).to_be_enabled()
                page.locator("#processed").uncheck()
                expect(page.locator("#speed")).to_be_disabled()
                expect(page.locator("#enhance")).to_be_disabled()
                with page.expect_download(timeout=90_000) as download:
                    page.locator("#export-wav").click()
                original = project()["exports"][-1]
                assert original["effective_speed"]==1.0
                assert hashlib.sha256(Path(download.value.path()).read_bytes()).hexdigest()==original["sha256"]
                expect(page.locator("#processed")).to_be_enabled()
                page.locator("#processed").check()
                page.locator("#enhance").check()
                page.locator("#preview-master").click()
                expect(page.locator("#master-caption")).to_contain_text("volume adjusted",timeout=30_000)
                expect(page.locator("#preview-master")).to_be_enabled()
                assert hashes(project())==before_exports
                page.reload()
                expect(page.locator("#title")).to_have_value("React narration workflow")
                expect(page.locator("#enhance")).to_be_checked()
                expect(page.locator("#master-panel")).to_be_visible()
                page.locator("#voice-settings summary").click()
                page.locator("#reference-label").fill("Future QA narrator")
                page.locator("#reference-file").set_input_files(reference)
                page.locator("#reference-transcript").fill(transcript)
                page.locator("#reference-rights").check()
                page.locator('#reference-form button[type="submit"]').click()
                expect(page.locator("#notice")).to_contain_text("Reference saved",timeout=30_000)
                expect(page.locator("#voice-label")).to_have_text("React QA narrator")
                page.locator("#new-project").click()
                expect(page.locator("#voice-label")).to_have_text("Future QA narrator")
                page.locator("#title").fill("New reference project")
                page.locator("#script").fill("A new project uses the latest authorized narrator reference.")
                page.locator("#generate").click()
                expect(page.locator("#progress-label")).to_have_text("Narration saved.",timeout=180_000)
                expect(page.locator("#generate")).to_be_enabled()
                page.locator(f'#projects button[data-project-id="{pid}"]').click()
                expect(page.locator("#voice-label")).to_have_text("React QA narrator")
                assert hashes(project())==before_exports
                assert client.get(f"/api/projects/{pid}/segments/{saved['segments'][0]['id']}/audio",headers={"Range":"bytes=0-1023"}).status_code==206
                page.screenshot(path=str(RUN / "desktop.png"),full_page=True)
                page.set_viewport_size({"width":620,"height":900})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth + 1")
                page.screenshot(path=str(RUN / "narrow.png"),full_page=True)
                assert errors==[],errors
                assert external==[],external
                assert saved['engine_id']=='qwen3-tts-0.6b-base' and saved['schema_version']==2
                assert saved['narrator']['reference_transcript']==transcript
                assert updated['segments'][1]['text']==saved['segments'][1]['text']
                assert updated['segments'][1]['inference_text']!=saved['segments'][1]['text']
                report.update(status="passed",engine_id=saved['engine_id'],react_production_bundle=True,reference_upload=True,create_confirmation_cancel=True,
                    real_cuda_generation=True,sections=3,reload_reattaches_active_job=True,no_duplicate_generation=True,
                    unsaved_edits_preserved_through_polling=True,navigation_discard_cancel=True,single_section_regeneration=True,
                    old_and_unrelated_raws_preserved=True,audio_playback_survives_polling=True,media_ranges=True,
                    preview_master=True,exports=exports,selected_zip=True,original_speed_export=True,volume_adjustment=True,
                    saved_settings_and_export_reopen=True,replacement_affects_only_new_projects=True,
                    no_horizontal_overflow_at_620px=True,page_errors=errors,external_requests=external)
                browser.close()
            # Restart the real server with a simulated interrupted manifest and
            # verify recovery never rewrites the previous completed recording.
            stop(process)
            process=None
            manifest=RUN / "data/projects" / pid / "project.json"
            state=json.loads(manifest.read_text(encoding="utf-8"))
            unchanged={s['id']:s['sha256'] for s in state['segments']}
            state['segments'][0].update(status='generating',stale=True,last_attempt_seed=2468)
            state['segments'][0]['attempts'].append({'status':'generating','seed':2468,'inference_text':state['segments'][0]['text']})
            manifest.write_text(json.dumps(state,indent=2),encoding="utf-8")
            process,health=start(log)
            assert not health['engine_loaded'] and health['active_job'] is None
            restored=httpx.get(BASE+f"/api/projects/{pid}").json()
            assert restored['segments'][0]['status']=='pending' and restored['segments'][0]['last_attempt_seed']==2468
            assert restored['segments'][0]['attempts'][-1]['status']=='interrupted'
            assert restored['narrator']['reference_transcript']==transcript
            assert all(hashlib.sha256((RUN/'data'/s['audio_path']).read_bytes()).hexdigest()==unchanged[s['id']] for s in restored['segments'])
            assert httpx.get(BASE+f"/api/projects/{pid}/segments/{restored['segments'][0]['id']}/audio").status_code==200
            assert httpx.get(BASE+f"/api/projects/{pid}/exports/{restored['exports'][-1]['id']}/download").status_code==200
            report.update(restart_reopen=True,simulated_interrupted_job_recovery=True,narrator_snapshot_persisted=True,
                          offline_external_sockets_blocked=True,project_id=pid)
            report['generation_metrics']=[s['metrics'] for s in restored['segments']]
            report['generation_parameters']=[s['generation_parameters'] for s in restored['segments']]

        except Exception:
            import traceback
            report.update(status="failed",error=traceback.format_exc())
            raise
        finally:
            stop(process)
            (RUN / "report.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
            print(json.dumps({"status":report["status"],"results":str(RUN)},indent=2),flush=True)


if __name__=="__main__":
    main()
