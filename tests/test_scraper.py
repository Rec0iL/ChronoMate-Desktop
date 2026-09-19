"""
Tests for HTML scraper logic
"""

import unittest
from core.poller import parse_chrono_html, is_chrono_page


class TestScraper(unittest.TestCase):
    def test_chrono_page_detection(self):
        valid_html = "<html><body><h1>HT-X3000 Chrono</h1><div>FireRate: 600 r/m</div><div>01: 99.5 m/s</div></body></html>"
        invalid_html = "<html><body><h1>Router Admin Page</h1><div>Status: Connected</div></body></html>"

        self.assertTrue(is_chrono_page(valid_html))
        self.assertFalse(is_chrono_page(invalid_html))

    def test_chrono_html_parsing(self):
        sample_html = """
        <html>
        <body>
            <div>Fire Rate: 720.5</div>
            <div>01: 100.2</div>
            <div>02: 101.5</div>
            <div>03: 99.8</div>
        </body>
        </html>
        """
        fire_rate, shots = parse_chrono_html(sample_html)
        self.assertEqual(fire_rate, 720.5)
        self.assertEqual(shots, [100.2, 101.5, 99.8])


if __name__ == "__main__":
    unittest.main()
