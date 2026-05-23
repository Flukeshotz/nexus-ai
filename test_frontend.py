import unittest
from html.parser import HTMLParser

class NexusHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags = set()
        self.ids = set()
        self.classes = set()

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag)
        for attr, value in attrs:
            if attr == 'id':
                self.ids.add(value)
            elif attr == 'class':
                self.classes.update(value.split())

class TestFrontend(unittest.TestCase):
    def setUp(self):
        with open('frontend/index.html', 'r') as f:
            self.html = f.read()
        self.parser = NexusHTMLParser()
        self.parser.feed(self.html)
        
        with open('frontend/app.js', 'r') as f:
            self.js = f.read()

    def test_core_elements_exist(self):
        # Header and Nav
        self.assertIn('app-header', self.parser.ids)
        self.assertIn('desktop-nav', self.parser.ids)
        self.assertIn('mobile-nav', self.parser.ids)
        
        # Main content area
        self.assertIn('app-main', self.parser.ids)
        
        # Chat Interface
        self.assertIn('chat-panel', self.parser.ids)
        self.assertIn('chat-fab', self.parser.ids)
        self.assertIn('chat-messages', self.parser.ids)
        self.assertIn('chat-input', self.parser.ids)

    def test_js_views_exist(self):
        # Views must be rendered by JS
        self.assertIn('renderDashboard()', self.js)
        self.assertIn('renderPortfolio()', self.js)
        self.assertIn('renderInsights()', self.js)
        self.assertIn('renderOnboarding()', self.js)
        
    def test_js_plotly_integration(self):
        # Plotly integration for portfolio view
        self.assertIn('Plotly.newPlot', self.js)
        self.assertIn('plot-allocation', self.js)
        self.assertIn('plot-performance', self.js)

if __name__ == '__main__':
    unittest.main()
