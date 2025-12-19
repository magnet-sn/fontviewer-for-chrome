import sys
from functools import lru_cache
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLineEdit, QLabel, QPushButton, 
                             QSlider, QListWidget, QListWidgetItem, QColorDialog,
                             QCheckBox, QFrame, QStyle, QStyledItemDelegate,
                             QGroupBox, QGridLayout, QScrollArea, QSizePolicy,
                             QSpinBox)
from PyQt6.QtGui import (QFont, QFontDatabase, QColor, QPainter, QPainterPath, 
                         QPen, QBrush, QFontMetrics, QPixmap, QAction)
from PyQt6.QtCore import Qt, QSize, QRect, QRectF, QPoint, QEvent

# --- 描画キャッシュ ---

@lru_cache(maxsize=500)
def generate_card_pixmap(cache_key):
    """
    カードの描画内容をQPixmapとして生成しキャッシュする。
    """
    (family, text, size_px, slot_num, is_dark_ui, text_col_rgba, edge_col_rgba, bg_col_rgba, is_bold, is_italic, width, height) = cache_key
    
    # 描画用キャンバス
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    
    # --- 色の復元 ---
    text_color = QColor(*text_col_rgba)
    edge_color = QColor(*edge_col_rgba) if edge_col_rgba is not None else None
    
    # 背景色決定ロジック
    if bg_col_rgba:
        bg_base = QColor(*bg_col_rgba)
    else:
        bg_base = QColor(20, 20, 20) if is_dark_ui else QColor(255, 255, 255)

    meta_color = QColor(150, 150, 150) if is_dark_ui else QColor(100, 100, 100)
        
    # ピン留め時の背景色調整
    is_pinned = slot_num > 0
    if is_pinned:
        # 視認性を確保しつつピン留め感を出す
        if bg_base.lightness() < 128:
            card_bg = bg_base.lighter(150)
        else:
            card_bg = QColor(230, 240, 255)
    else:
        card_bg = bg_base
    
    # --- 1. カード背景描画 ---
    rect = QRect(0, 0, width, height)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(card_bg)
    painter.drawRoundedRect(rect, 8, 8)
    
    # ピン留め枠強調
    if is_pinned:
        painter.setPen(QPen(QColor(100, 150, 255), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(rect.adjusted(1,1,-1,-1), 8, 8)

    # --- 2. ヘッダー（フォント名）描画 ---
    painter.setPen(meta_color)
    sys_font = QFont() # UI用システムフォント
    sys_font.setPointSize(8)
    painter.setFont(sys_font)
    
    name_rect = QRect(8, 4, width - 40, 20)
    pin_mark = f"[{slot_num}] " if is_pinned else ""
    painter.drawText(name_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{pin_mark}{family}")
    
    # ピンバッジ
    if is_pinned:
        badge_size = 18
        badge_rect = QRect(width - 24, 4, badge_size, badge_size)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(100, 150, 255))
        painter.drawEllipse(badge_rect)
        
        painter.setPen(QColor(255, 255, 255))
        font_badge = QFont()
        font_badge.setPointSize(10)
        font_badge.setBold(True)
        painter.setFont(font_badge)
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, str(slot_num))

    # --- 3. サンプルテキスト描画 (パスによる完全制御) ---
    
    target_font = QFont(family)
    target_font.setPixelSize(size_px)
    target_font.setBold(is_bold)
    target_font.setItalic(is_italic)
    target_font.setStyleStrategy(QFont.StyleStrategy.NoFontMerging)
    
    fm = QFontMetrics(target_font)
    
    content_rect = QRect(10, 24, width - 20, height - 24)
    text_y = content_rect.center().y() + (fm.capHeight() / 2)
    current_x = content_rect.left()
    
    # すべての形状（文字・豆腐）を1つのパスにまとめる
    path = QPainterPath()
    
    for char in text:
        if current_x > width - 5: break

        if not fm.inFont(char):
            # ☒ (豆腐) -> パスとして追加（これで縁取りも効くようになる）
            box_size = size_px * 0.8
            box_rect = QRectF(current_x, text_y - box_size, box_size, box_size)
            path.addRect(box_rect)
            # バツ印もパスに追加
            path.moveTo(box_rect.topLeft())
            path.lineTo(box_rect.bottomRight())
            path.moveTo(box_rect.topRight())
            path.lineTo(box_rect.bottomLeft())
            
            current_x += box_size + (size_px * 0.1)
        else:
            # 通常文字 -> パスに追加
            path.addText(current_x, text_y, target_font, char)
            current_x += fm.horizontalAdvance(char)
    
    # --- 描画実行 (レイヤー方式) ---
    
    # Layer 1: 縁取り (Stroke)
    if edge_col_rgba is not None:
        # 文字の中身が上書きされることを考慮し、少し太めに設定する
        stroke_width = size_px * 0.10
        pen = QPen(edge_color, stroke_width)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin) # 角を丸くしてトゲトゲ防止
        
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
    
    # Layer 2: 中身 (Fill)
    # 縁取りの上に描画することで、文字が痩せるのを防ぐ
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(text_color)
    painter.drawPath(path)
    
    painter.end()
    return pixmap


class FontRenderDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.dark_mode = False
        self.text_color = QColor(0, 0, 0)
        self.edge_color = None
        self.bg_color = None
        self.sample_text = "サンプル&Sample"
        
        self.pixel_size = 32
        self.is_bold = False
        self.is_italic = False
        
        self.size_cache = {}

    def clear_cache(self):
        self.size_cache.clear()
        generate_card_pixmap.cache_clear()
        
    def _get_rgba(self, color):
        if color and color.isValid():
            return (color.red(), color.green(), color.blue(), color.alpha())
        return None

    def get_content_size(self, family):
        if family in self.size_cache:
            return self.size_cache[family]
        
        f = QFont(family)
        f.setPixelSize(self.pixel_size)
        f.setBold(self.is_bold)
        f.setItalic(self.is_italic)
        f.setStyleStrategy(QFont.StyleStrategy.NoFontMerging)
        fm = QFontMetrics(f)
        
        text_w = 0
        for char in self.sample_text:
            if fm.inFont(char):
                text_w += fm.horizontalAdvance(char)
            else:
                text_w += self.pixel_size 
        
        w = max(100, text_w + 30)
        h = 24 + (self.pixel_size * 1.5) + 10
        
        size = QSize(int(w), int(h))
        self.size_cache[family] = size
        return size

    def paint(self, painter, option, index):
        font_family = index.data(Qt.ItemDataRole.UserRole)
        slot_num = index.data(Qt.ItemDataRole.UserRole + 1)
        if slot_num is None: slot_num = 0
        
        rect = option.rect
        
        if option.state & QStyle.StateFlag.State_Selected:
            painter.fillRect(rect, option.palette.highlight())
        
        margin = 4
        card_rect = rect.adjusted(margin, margin, -margin, -margin)
        
        t_col = self._get_rgba(self.text_color)
        e_col = self._get_rgba(self.edge_color)
        b_col = self._get_rgba(self.bg_color)
        
        key = (
            font_family,
            self.sample_text,
            self.pixel_size,
            slot_num,
            self.dark_mode,
            t_col,
            e_col,
            b_col,
            self.is_bold,
            self.is_italic,
            card_rect.width(),
            card_rect.height()
        )
        
        pixmap = generate_card_pixmap(key)
        
        x_offset = (rect.width() - pixmap.width()) // 2
        y_offset = (rect.height() - pixmap.height()) // 2
        target_point = rect.topLeft() + QPoint(max(0, x_offset), max(0, y_offset))
        
        painter.drawPixmap(target_point, pixmap)

    def sizeHint(self, option, index):
        font_family = index.data(Qt.ItemDataRole.UserRole)
        if not font_family: return QSize(100, 50)
        base_size = self.get_content_size(font_family)
        return base_size + QSize(8, 8)


class PinnedFontsWidget(QWidget):
    def __init__(self, delegate, parent=None):
        super().__init__(parent)
        self.delegate = delegate
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(10)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.slots = {} 
        self.pinned_data = {} 

    def update_slots(self, pinned_dict):
        self.pinned_data = pinned_dict
        
        for i in reversed(range(self.layout.count())): 
            self.layout.itemAt(i).widget().setParent(None)
        
        self.slots.clear()
        
        for num in range(1, 6):
            if num in pinned_dict and pinned_dict[num]:
                family = pinned_dict[num]
                
                lbl = QLabel()
                lbl.setStyleSheet("border: 1px dashed gray; border-radius: 4px;")
                
                size = self.delegate.get_content_size(family)
                lbl.setFixedSize(size)
                
                t_col = self.delegate._get_rgba(self.delegate.text_color)
                e_col = self.delegate._get_rgba(self.delegate.edge_color)
                b_col = self.delegate._get_rgba(self.delegate.bg_color)
                
                key = (
                    family,
                    self.delegate.sample_text,
                    self.delegate.pixel_size,
                    num, 
                    self.delegate.dark_mode,
                    t_col,
                    e_col,
                    b_col,
                    self.delegate.is_bold,
                    self.delegate.is_italic,
                    size.width(),
                    size.height()
                )
                pixmap = generate_card_pixmap(key)
                lbl.setPixmap(pixmap)
                
                self.layout.addWidget(lbl)
                self.slots[num] = lbl


class FontViewerApp(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Font Viewer - Ultimate Edition")
        self.resize(1100, 800)
        
        self.pinned_slots = {1: None, 2: None, 3: None, 4: None, 5: None}
        self.all_fonts = QFontDatabase.families()
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- コントロールパネル ---
        control_panel = QFrame()
        control_layout = QGridLayout(control_panel)
        control_panel.setFrameShape(QFrame.Shape.StyledPanel)
        
        # 1行目: テキスト入力
        self.input_text = QLineEdit("サンプル&Sample")
        self.input_text.setPlaceholderText("プレビューする文章...")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("フォント名検索...")
        self.search_box.setClearButtonEnabled(True)
        
        control_layout.addWidget(QLabel("文章:"), 0, 0)
        control_layout.addWidget(self.input_text, 0, 1)
        control_layout.addWidget(QLabel("検索:"), 0, 2)
        control_layout.addWidget(self.search_box, 0, 3)

        # 2行目: 設定 & スタイル
        style_layout = QHBoxLayout()
        self.dark_mode_chk = QCheckBox("ダークモード")
        self.ontop_chk = QCheckBox("常に最前面")
        self.bold_chk = QCheckBox("太字")
        self.italic_chk = QCheckBox("斜体")
        
        style_layout.addWidget(self.dark_mode_chk)
        style_layout.addWidget(self.ontop_chk)
        style_layout.addSpacing(20)
        style_layout.addWidget(self.bold_chk)
        style_layout.addWidget(self.italic_chk)
        style_layout.addStretch()
        
        control_layout.addLayout(style_layout, 1, 0, 1, 4)

        # 3行目: サイズ & 色
        size_color_layout = QHBoxLayout()
        
        # サイズスライダー & SpinBox
        self.px_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.px_size_slider.setRange(10, 150)
        self.px_size_slider.setValue(32)
        
        self.px_size_spin = QSpinBox()
        self.px_size_spin.setRange(10, 150)
        self.px_size_spin.setValue(32)
        self.px_size_spin.setSuffix(" px")
        
        size_color_layout.addWidget(QLabel("文字サイズ:"))
        size_color_layout.addWidget(self.px_size_slider)
        size_color_layout.addWidget(self.px_size_spin)
        size_color_layout.addSpacing(20)
        
        # 色設定
        self.text_color_btn = QPushButton("文字色")
        self.bg_color_btn = QPushButton("背景色")
        
        # 縁取りボタン（右クリック機能付き）
        self.edge_color_btn = QPushButton("縁取り(なし)")
        self.edge_color_btn.setToolTip("左クリック: 色を選択\n右クリック: 解除")
        self.edge_color_btn.installEventFilter(self) # イベントフィルターで右クリック検知
        
        self.current_text_color = QColor(0, 0, 0)
        self.current_bg_color = None 
        self.edge_color = None
        
        size_color_layout.addWidget(self.text_color_btn)
        size_color_layout.addWidget(self.bg_color_btn)
        size_color_layout.addWidget(self.edge_color_btn)
        
        control_layout.addLayout(size_color_layout, 2, 0, 1, 4)
        main_layout.addWidget(control_panel)
        
        # --- 比較用フォントエリア ---
        self.delegate = FontRenderDelegate()
        
        self.pinned_area_scroll = QScrollArea()
        self.pinned_area_scroll.setFixedHeight(120)
        self.pinned_area_scroll.setWidgetResizable(True)
        self.pinned_area_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.pinned_area_scroll.setStyleSheet("background-color: transparent; border-bottom: 2px solid #ccc;")
        
        self.pinned_widget = PinnedFontsWidget(self.delegate)
        self.pinned_area_scroll.setWidget(self.pinned_widget)
        
        main_layout.addWidget(self.pinned_area_scroll)
        
        self.info_label = QLabel("フォントを選択してキーボードの [1]〜[5] を押すと上部に固定・比較できます")
        self.info_label.setStyleSheet("color: gray; font-size: 11px; padding: 4px;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.info_label)

        # --- メインフォントリスト ---
        self.list_view = QListWidget()
        self.list_view.setViewMode(QListWidget.ViewMode.IconMode)
        self.list_view.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.list_view.setMovement(QListWidget.Movement.Static)
        self.list_view.setUniformItemSizes(False)
        self.list_view.setSpacing(6)
        self.list_view.setGridSize(QSize()) 
        
        self.list_view.setItemDelegate(self.delegate)
        self.list_view.installEventFilter(self)
        
        main_layout.addWidget(self.list_view)

        # --- シグナル ---
        self.input_text.textChanged.connect(self.update_content)
        self.search_box.textChanged.connect(self.filter_fonts)
        self.dark_mode_chk.toggled.connect(self.toggle_dark_mode)
        self.ontop_chk.toggled.connect(self.toggle_ontop)
        self.bold_chk.toggled.connect(self.update_style)
        self.italic_chk.toggled.connect(self.update_style)
        
        self.px_size_slider.valueChanged.connect(self.px_size_spin.setValue)
        self.px_size_spin.valueChanged.connect(self.px_size_slider.setValue)
        self.px_size_slider.valueChanged.connect(self.update_sizes)
        
        self.text_color_btn.clicked.connect(self.pick_text_color)
        self.bg_color_btn.clicked.connect(self.pick_bg_color)
        self.edge_color_btn.clicked.connect(self.pick_edge_color)

        self.update_sizes()
        self.load_fonts()
        self.update_pinned_area()

    def eventFilter(self, source, event):
        # 1. リストビューでのキー入力 (1-5でピン留め)
        if event.type() == QEvent.Type.KeyPress and source is self.list_view:
            key = event.key()
            if Qt.Key.Key_1 <= key <= Qt.Key.Key_5:
                slot = key - Qt.Key.Key_0
                self.toggle_pin_selection(slot)
                return True
        
        # 2. 縁取りボタンでの右クリック (解除)
        if event.type() == QEvent.Type.MouseButtonPress and source is self.edge_color_btn:
            if event.button() == Qt.MouseButton.RightButton:
                self.clear_edge_color()
                return True

        return super().eventFilter(source, event)

    def toggle_pin_selection(self, slot):
        items = self.list_view.selectedItems()
        if not items: return
            
        current_item = items[0]
        font_family = current_item.data(Qt.ItemDataRole.UserRole)
        
        if self.pinned_slots[slot] == font_family:
            self.pinned_slots[slot] = None
        else:
            self.pinned_slots[slot] = font_family
            for s, fam in self.pinned_slots.items():
                if s != slot and fam == font_family:
                    self.pinned_slots[s] = None

        self.update_pinned_area()
        self.list_view.viewport().update()

    def update_pinned_area(self):
        self.pinned_widget.update_slots(self.pinned_slots)
        sample_font = self.all_fonts[0]
        size = self.delegate.get_content_size(sample_font)
        new_height = size.height() + 30 
        self.pinned_area_scroll.setFixedHeight(min(300, max(100, new_height)))

    def load_fonts(self):
        self.list_view.clear()
        filter_text = self.search_box.text().lower()
        filtered = [f for f in self.all_fonts if filter_text in f.lower()]
        filtered.sort(key=lambda x: x.lower())
        
        for fam in filtered:
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, fam)
            slot_num = 0
            for s, f in self.pinned_slots.items():
                if f == fam:
                    slot_num = s
                    break
            item.setData(Qt.ItemDataRole.UserRole + 1, slot_num)
            self.list_view.addItem(item)

    def update_content(self):
        text = self.input_text.text()
        if not text: text = " "
        self.delegate.sample_text = text
        self.delegate.clear_cache()
        self.list_view.doItemsLayout()
        self.list_view.viewport().update()
        self.update_pinned_area()

    def update_style(self):
        self.delegate.is_bold = self.bold_chk.isChecked()
        self.delegate.is_italic = self.italic_chk.isChecked()
        self.delegate.clear_cache()
        self.list_view.doItemsLayout()
        self.list_view.viewport().update()
        self.update_pinned_area()

    def filter_fonts(self):
        self.load_fonts()

    def update_sizes(self):
        px = self.px_size_slider.value()
        self.delegate.pixel_size = px
        self.delegate.clear_cache()
        self.list_view.doItemsLayout()
        self.list_view.viewport().update()
        self.update_pinned_area()

    def toggle_dark_mode(self, checked):
        self.delegate.dark_mode = checked
        if checked:
            self.current_text_color = QColor(255, 255, 255)
            self.current_bg_color = QColor(20, 20, 20)
        else:
            self.current_text_color = QColor(0, 0, 0)
            self.current_bg_color = None
            
        self.delegate.text_color = self.current_text_color
        self.delegate.bg_color = self.current_bg_color
        
        self.delegate.clear_cache()
        
        style = """
            QLineEdit { border: 1px solid #999; padding: 4px; border-radius: 4px; }
            QScrollArea { border: none; border-bottom: 1px solid #666; }
        """
        if checked:
            self.setStyleSheet("""
                QMainWindow, QWidget { background-color: #000000; color: #FFFFFF; }
                QLineEdit { background-color: #222222; color: #FFFFFF; border: 1px solid #555; }
                QListWidget { background-color: #000000; border: none; }
                QPushButton { background-color: #333; color: white; border: 1px solid #555; padding: 5px; }
                QCheckBox { color: white; }
                QLabel { color: white; }
                QSpinBox { background-color: #222; color: white; border: 1px solid #555; }
            """ + style)
        else:
            self.setStyleSheet(style)
        self.list_view.viewport().update()
        self.update_pinned_area()

    def toggle_ontop(self, checked):
        if checked:
            self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowStaysOnTopHint)
        self.show()

    def _open_color_dialog(self, initial_color, title):
        dialog = QColorDialog(initial_color, self)
        dialog.setWindowTitle(title)
        dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog)
        if dialog.exec():
            return dialog.selectedColor()
        return None

    def pick_text_color(self):
        col = self._open_color_dialog(self.current_text_color, "文字色を選択")
        if col and col.isValid():
            self.current_text_color = col
            self.delegate.text_color = col
            self.delegate.clear_cache()
            self.list_view.viewport().update()
            self.update_pinned_area()

    def pick_bg_color(self):
        initial = self.current_bg_color if self.current_bg_color else QColor(255, 255, 255)
        col = self._open_color_dialog(initial, "背景色を選択")
        if col and col.isValid():
            self.current_bg_color = col
            self.delegate.bg_color = col
            self.delegate.clear_cache()
            self.list_view.viewport().update()
            self.update_pinned_area()

    def pick_edge_color(self):
        initial = self.edge_color if self.edge_color else QColor(255, 255, 255)
        col = self._open_color_dialog(initial, "縁取り色を選択")
        
        if col and col.isValid():
            self.edge_color = col
            self.edge_color_btn.setText("縁取り(右クリで解除)")
            self.delegate.edge_color = self.edge_color
            self.delegate.clear_cache()
            self.list_view.viewport().update()
            self.update_pinned_area()

    def clear_edge_color(self):
        """右クリックで呼び出される縁取り解除処理"""
        self.edge_color = None
        self.edge_color_btn.setText("縁取り(なし)")
        self.delegate.edge_color = None
        self.delegate.clear_cache()
        self.list_view.viewport().update()
        self.update_pinned_area()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    if hasattr(Qt.ApplicationAttribute, 'AA_UseHighDpiPixmaps'):
        app.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)
    window = FontViewerApp()
    window.show()
    sys.exit(app.exec())

