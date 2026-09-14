import sys
import os
from PySide6.QtWidgets import QApplication
from app.gui.main_window import MainWindow
from app.config.settings import settings
from app.utils.logging import setup_logging, get_logger

logger = get_logger(__name__)

def main():
    setup_logging(settings.log_level)
    logger.info("Starting English -> Bangla PDF Translator application...")

    # Enable high DPI scaling on displays if available
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"

    app = QApplication(sys.argv)
    app.setApplicationName("English -> Bangla PDF Translator")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
