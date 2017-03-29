import unittest
from utils import html_to_text, get_simhash_distance, sort_resources
from fixtures import example_html_str, example_diff_html_str

class TestUtils(unittest.TestCase):
    def test_html_to_text(self):
        self.assertTrue("<script>" in example_html_str)
        self.assertTrue("<head>" in example_html_str)

        text_str = html_to_text(example_html_str)
        self.assertFalse("<script>" in text_str)
        self.assertFalse("<head>" in text_str)

    def test_get_simhash_distance(self):
        distance = get_simhash_distance(example_html_str, example_diff_html_str)
        self.assertTrue(distance > 0)

        example_text = html_to_text(example_html_str)
        example_text_2 = html_to_text(example_diff_html_str)
        distance = get_simhash_distance(example_text, example_text_2)
        self.assertEqual(distance, 0)

    def test_sort_resources(self):
        collection_one = {
            '.png': ['img.png', 'img2.png'],
            '.js': ['script.js'],
            '.jpg': ['img.jpg'],
        }

        collection_two = {
            '.png': ['img2.png', 'img3.png'],
            '.js': ['script.js'],
            '.jpg': ['img5.jpg'],
        }

        missing, added, common = sort_resources(collection_one, collection_two)

        self.assertTrue('img.png' in missing['.png'])
        self.assertTrue('img2.png' not in missing['.png'])
        self.assertTrue('img5.jpg' in added['.jpg'])
        self.assertEqual(['script.js'], common['.js'])

def main():
    unittest.main()

if __name__ == '__main__':
    main()