# ui/widgets.py

from PyQt5.QtWidgets import QAbstractButton, QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import pyqtSignal, QPropertyAnimation, QEasingCurve, pyqtProperty, QRectF, Qt
from PyQt5.QtGui import QPainter, QBrush, QColor, QPen

class ToggleSwitch(QAbstractButton):
    """iOS tarzı animasyonlu toggle switch"""
    stateChanged = pyqtSignal(int)

    def __init__(self, parent=None, width=36, height=20):
        super().__init__(parent)
        self.setCheckable(True)
        self._thumb_pos = 0.0
        self._animation = QPropertyAnimation(self, b"thumbPos")
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.setFixedSize(width, height)
        self._border_radius = height // 2
        self._track_color_on = QColor(52, 199, 89)
        self._track_color_off = QColor(127, 140, 141)
        self._thumb_color = QColor(255, 255, 255)

    @pyqtProperty(float)
    def thumbPos(self):
        return self._thumb_pos

    @thumbPos.setter
    def thumbPos(self, pos):
        self._thumb_pos = pos
        self.update()

    def nextCheckState(self):
        pass

    def setChecked(self, checked):
        if self.isChecked() == checked:
            return
        super().setChecked(checked)
        self._update_thumb_pos()
        self._start_animation()
        self.stateChanged.emit(2 if checked else 0)

    def _start_animation(self):
        self._animation.stop()
        self._animation.setEndValue(1.0 if self.isChecked() else 0.0)
        self._animation.start()

    def _update_thumb_pos(self):
        self._thumb_pos = 1.0 if self.isChecked() else 0.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        track_rect = QRectF(0, 0, self.width(), self.height())
        track_color = self._track_color_on if self.isChecked() else self._track_color_off
        painter.setBrush(QBrush(track_color))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(track_rect, self._border_radius, self._border_radius)
        thumb_margin = 2
        thumb_size = self.height() - 2 * thumb_margin
        thumb_x = thumb_margin + self._thumb_pos * (self.width() - thumb_size - 2 * thumb_margin)
        thumb_rect = QRectF(thumb_x, thumb_margin, thumb_size, thumb_size)
        painter.setBrush(QBrush(self._thumb_color))
        painter.drawEllipse(thumb_rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setChecked(not self.isChecked())
        super().mousePressEvent(event)


class ToggleSwitchWithLabel(QWidget):
    """Yanında metin bulunan toggle switch"""
    stateChanged = pyqtSignal(int)

    def __init__(self, text="", width=50, height=24, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.toggle = ToggleSwitch(width=width, height=height)
        self.label = QLabel(text)
        self.label.setStyleSheet("color: #ecf0f1; font-size: 12px;")
        layout.addWidget(self.toggle)
        layout.addWidget(self.label)
        layout.addStretch()
        self.toggle.stateChanged.connect(self._on_toggle_state)

    def _on_toggle_state(self, state):
        self.stateChanged.emit(state)

    def isChecked(self):
        return self.toggle.isChecked()

    def setChecked(self, checked):
        self.toggle.setChecked(checked)

    def setText(self, text):
        self.label.setText(text)