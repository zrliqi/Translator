import unittest
from app.utils.page_selection import PageSelection, PageSelectionMode

class TestPageSelection(unittest.TestCase):
    def test_all_pages(self):
        sel = PageSelection(mode=PageSelectionMode.ALL)
        is_valid, err = sel.validate(104)
        self.assertTrue(is_valid)
        self.assertEqual(err, "")
        self.assertEqual(sel.get_selected_pages(104), list(range(1, 105)))

    def test_page_range_5_to_5(self):
        sel = PageSelection(mode=PageSelectionMode.RANGE, range_from=5, range_to=5)
        is_valid, err = sel.validate(104)
        self.assertTrue(is_valid)
        self.assertEqual(sel.get_selected_pages(104), [5])

    def test_page_range_5_to_9(self):
        sel = PageSelection(mode=PageSelectionMode.RANGE, range_from=5, range_to=9)
        is_valid, err = sel.validate(104)
        self.assertTrue(is_valid)
        self.assertEqual(sel.get_selected_pages(104), [5, 6, 7, 8, 9])

    def test_page_range_9_to_11(self):
        sel = PageSelection(mode=PageSelectionMode.RANGE, range_from=9, range_to=11)
        is_valid, err = sel.validate(104)
        self.assertTrue(is_valid)
        self.assertEqual(sel.get_selected_pages(104), [9, 10, 11])

    def test_specific_pages_single(self):
        sel = PageSelection(mode=PageSelectionMode.SPECIFIC, specific_input="5")
        is_valid, err = sel.validate(104)
        self.assertTrue(is_valid)
        self.assertEqual(sel.get_selected_pages(104), [5])

    def test_specific_pages_list(self):
        sel = PageSelection(mode=PageSelectionMode.SPECIFIC, specific_input="5,9,11")
        is_valid, err = sel.validate(104)
        self.assertTrue(is_valid)
        self.assertEqual(sel.get_selected_pages(104), [5, 9, 11])

    def test_specific_pages_combination(self):
        sel = PageSelection(mode=PageSelectionMode.SPECIFIC, specific_input="5, 9-11, 20")
        is_valid, err = sel.validate(104)
        self.assertTrue(is_valid)
        self.assertEqual(sel.get_selected_pages(104), [5, 9, 10, 11, 20])

    def test_first_page(self):
        sel = PageSelection(mode=PageSelectionMode.SPECIFIC, specific_input="1")
        is_valid, err = sel.validate(104)
        self.assertTrue(is_valid)
        self.assertEqual(sel.get_selected_pages(104), [1])

    def test_last_page(self):
        sel = PageSelection(mode=PageSelectionMode.SPECIFIC, specific_input="104")
        is_valid, err = sel.validate(104)
        self.assertTrue(is_valid)
        self.assertEqual(sel.get_selected_pages(104), [104])

    def test_full_range_specific(self):
        sel = PageSelection(mode=PageSelectionMode.SPECIFIC, specific_input="1-104")
        is_valid, err = sel.validate(104)
        self.assertTrue(is_valid)
        self.assertEqual(sel.get_selected_pages(104), list(range(1, 105)))

    def test_invalid_page_0(self):
        sel1 = PageSelection(mode=PageSelectionMode.RANGE, range_from=0, range_to=5)
        is_valid1, err1 = sel1.validate(104)
        self.assertFalse(is_valid1)
        self.assertIn("at least 1", err1)

        sel2 = PageSelection(mode=PageSelectionMode.SPECIFIC, specific_input="0")
        is_valid2, err2 = sel2.validate(104)
        self.assertFalse(is_valid2)
        self.assertIn("at least 1", err2)

    def test_invalid_page_exceeds_total(self):
        sel1 = PageSelection(mode=PageSelectionMode.RANGE, range_from=1, range_to=105)
        is_valid1, err1 = sel1.validate(104)
        self.assertFalse(is_valid1)
        self.assertIn("exceeds total pages", err1)

        sel2 = PageSelection(mode=PageSelectionMode.SPECIFIC, specific_input="105")
        is_valid2, err2 = sel2.validate(104)
        self.assertFalse(is_valid2)
        self.assertIn("exceeds total pages", err2)

    def test_invalid_range_order(self):
        sel1 = PageSelection(mode=PageSelectionMode.RANGE, range_from=10, range_to=5)
        is_valid1, err1 = sel1.validate(104)
        self.assertFalse(is_valid1)
        self.assertIn("cannot be greater", err1)

        sel2 = PageSelection(mode=PageSelectionMode.SPECIFIC, specific_input="10-5")
        is_valid2, err2 = sel2.validate(104)
        self.assertFalse(is_valid2)
        self.assertIn("greater than end page", err2)

    def test_malformed_specific_input(self):
        malformed_inputs = ["abc", "5--9", "5-", ",5", "5, ,9"]
        for inp in malformed_inputs:
            sel = PageSelection(mode=PageSelectionMode.SPECIFIC, specific_input=inp)
            is_valid, err = sel.validate(104)
            self.assertFalse(is_valid, f"Input '{inp}' should be invalid")
            self.assertTrue(len(err) > 0)

    def test_empty_specific_input(self):
        sel = PageSelection(mode=PageSelectionMode.SPECIFIC, specific_input="   ")
        is_valid, err = sel.validate(104)
        self.assertFalse(is_valid)
        self.assertIn("cannot be empty", err)

if __name__ == "__main__":
    unittest.main()
