import unittest
import tempfile
from pathlib import Path
from app.document.paragraph_model import ParagraphModel
from app.processing.pipeline import JobState, JobManager
from app.translation.ai_recheck import AIRecheckEngine

class TestHumanReview(unittest.TestCase):
    def test_ai_recheck_engine(self):
        engine = AIRecheckEngine()
        para = ParagraphModel(id="p1_b1", text="She wanted to buy a present for her husband.")
        para.add_human_edit("সে তার স্বামীর জন্য একটি উপহার কিনতে চেয়েছিল।")

        res = engine.recheck_paragraph(para)
        self.assertIn(res.status, ["PASS", "SUGGESTION", "POTENTIAL ISSUE"])
        self.assertEqual(para.ai_recheck_status, res.status)
        self.assertEqual(para.review_status, "AI Rechecked")
        # Ensure human edit was NOT overwritten
        self.assertEqual(para.current_translation, "সে তার স্বামীর জন্য একটি উপহার কিনতে চেয়েছিল।")
    def test_paragraph_model_extensions(self):
        para = ParagraphModel(id="p1_b1", text="She wanted to buy a present for her husband.")
        self.assertEqual(para.source_text, "She wanted to buy a present for her husband.")
        self.assertEqual(para.current_translation, "")
        self.assertFalse(para.has_human_edit())

        # Set AI translation
        para.set_ai_translation("সে তার স্বামীর জন্য একটি উপহার কিনতে চেয়েছিল।")
        self.assertEqual(para.current_translation, "সে তার স্বামীর জন্য একটি উপহার কিনতে চেয়েছিল।")
        self.assertEqual(para.review_status, "AI Translated")

        # Add human edit
        human_text = "সে তার স্বামীর জন্য একটি সুন্দর উপহার কিনতে চেয়েছিল।"
        para.add_human_edit(human_text, editor="John Reviewer")

        self.assertTrue(para.has_human_edit())
        self.assertEqual(para.current_translation, human_text)
        self.assertEqual(para.review_status, "Human Edited")
        self.assertEqual(para.edited_by, "John Reviewer")
        self.assertEqual(len(para.revisions), 1)

    def test_protect_human_edits_from_ai_overwrite(self):
        para = ParagraphModel(id="p1_b2", text="The Della sold her hair.")
        para.set_ai_translation("ডেলা তার চুল বিক্রি করেছিল।")
        human_correction = "ডেলা তার সুন্দর চুলগুলো বিক্রি করে দিল।"
        para.add_human_edit(human_correction, editor="Jane Doe")

        # Attempt AI re-translation without force
        overwritten = para.set_ai_translation("নতুন এআই অনুবাদ", force_overwrite_human=False)
        self.assertFalse(overwritten)
        # Verify human edit was protected
        self.assertEqual(para.current_translation, human_correction)
        self.assertEqual(para.ai_translation, "নতুন এআই অনুবাদ")

    def test_version_history_and_revert(self):
        para = ParagraphModel(id="p1_b3", text="Hello world")
        para.set_ai_translation("হ্যালো ওয়ার্ল্ড")
        para.add_human_edit("ওহে বিশ্ব", editor="Reviewer 1")
        para.add_human_edit("হে বিশ্ব", editor="Reviewer 2")

        self.assertEqual(len(para.revisions), 2)
        self.assertEqual(para.current_translation, "হে বিশ্ব")

        # Revert to version 0 (AI original)
        reverted = para.revert_to_version(0)
        self.assertTrue(reverted)
        self.assertEqual(para.current_translation, "হ্যালো ওয়ার্ল্ড")

    def test_comments(self):
        para = ParagraphModel(id="p1_b4", text="Sample text")
        para.add_comment("Use a more natural Bangla expression.", author="Editor")
        self.assertEqual(len(para.comments), 1)
        self.assertEqual(para.comments[0]["author"], "Editor")
        self.assertEqual(para.comments[0]["text"], "Use a more natural Bangla expression.")

    def test_job_state_persistence_of_units(self):
        temp_dir = tempfile.TemporaryDirectory()
        db_path = Path(temp_dir.name) / "test_cache.db"
        jm = JobManager(db_path=db_path)

        para = ParagraphModel(id="p1_b1", text="Sample")
        para.set_ai_translation("নমুনা")
        para.add_human_edit("উন্নত নমুনা", editor="Reviewer")
        para.add_comment("Great translation!", author="Boss")

        job = JobState(
            job_id="test_job_1",
            source_pdf_path="sample.pdf",
            source_pdf_hash="hash123",
            total_pages=1,
            translated_map={para.id: para.current_translation},
            units_map={para.id: para.to_dict()}
        )
        jm.save_job(job)

        loaded_job = jm.load_job("test_job_1")
        self.assertIsNotNone(loaded_job)
        self.assertIn("p1_b1", loaded_job.units_map)

        restored_para = ParagraphModel.from_dict(loaded_job.units_map["p1_b1"])
        self.assertEqual(restored_para.current_translation, "উন্নত নমুনা")
        self.assertEqual(restored_para.review_status, "Human Edited")
        self.assertEqual(len(restored_para.comments), 1)

        # Test finding job by path
        found_job = jm.find_job_by_path("sample.pdf")
        self.assertIsNotNone(found_job)
        self.assertEqual(found_job.job_id, "test_job_1")

        temp_dir.cleanup()

if __name__ == '__main__':
    unittest.main()
