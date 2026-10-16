// SPDX-License-Identifier: LGPL-2.1-or-later
#include <QApplication>
#include <QBuffer>
#include <QElapsedTimer>
#include <QEventLoop>
#include <QGraphicsPathItem>
#include <QGraphicsScene>
#include <QGraphicsView>
#include <QPaintEvent>
#include <memory>
#include <limits>
#include <QScrollBar>
#include <QSvgGenerator>
#include <iostream>
#include <algorithm>
#include <stdexcept>
#include "NavigationPreview.h"

#define CHECK(expr) do { if (!(expr)) throw std::runtime_error(#expr); } while (false)
using TechDrawGui::NavigationPreview;

struct TestPreferences {
    bool partial = false, preview = false;
    bool GetBool(const char* key, bool) const {
        return QString::fromLatin1(key) == "PartialViewportUpdates" ? partial : preview;
    }
};
struct Preferences {
    static TestPreferences* getPreferenceGroup(const char*) {
        static TestPreferences prefs;
        return &prefs;
    }
};

// Compile the actual modified QGVPage paint method with a Qt-only fixture.
class QGVPage : public QGraphicsView {
public:
    enum class RendererType { Native, OpenGL, Image };
    explicit QGVPage(QGraphicsScene* scene) : QGraphicsView(scene), m_navigationPreview(std::make_unique<NavigationPreview>(this)) {
        setCacheMode(QGraphicsView::CacheBackground);
    }
    void paintEvent(QPaintEvent*) override;
    void setRenderer(RendererType);
    void beginNavigationPreview();
    void drawBackground(QPainter*, const QRectF&) override;
    struct TestProvider { bool getDrawPage() const { return true; } } provider;
    TestProvider* m_vpPage = &provider;
    bool drawBkg = true;
    QBrush background{Qt::white};
    QBrush* bkgBrush = &background;
    bool toolHandler = false, balloonPlacing = false;
    QColor getBackgroundColor() const { return Qt::white; }
    RendererType m_renderer = RendererType::Native;
    std::unique_ptr<NavigationPreview> m_navigationPreview;
    QImage m_image;
};
// Native QWidget tests; no OpenGL context or driver is required.
#define QT_NO_OPENGL
#include "navigation_paint.inc"
#undef QT_NO_OPENGL

class QGVNavStyle {
public:
    explicit QGVNavStyle(QGVPage* view) : m_view(view) {}
    QGVPage* getViewer() { return m_view; }
    void setAnchor() {}
    void zoom(double factor);
    void pan(QPoint point);
    QGVPage* m_view;
    bool m_zoomPending = false;
    QPoint panOrigin;
    int m_reversePan = 1, m_reverseScroll = 1;
};
#include "navigation_hooks.inc"

// The upstream solid background path, used solely as a pixel reference.
class OriginalBackgroundPage : public QGVPage {
public:
    explicit OriginalBackgroundPage(QGraphicsScene* scene) : QGVPage(scene) {}
    void drawBackground(QPainter* painter, const QRectF&) override {
        painter->save();
        painter->resetTransform();
        painter->setBrush(*bkgBrush);
        painter->drawRect(viewport()->rect().adjusted(-2, -2, 2, 2));
        painter->restore();
    }
};

struct CountedPath : QGraphicsPathItem {
    static int paints;
    void paint(QPainter* painter, const QStyleOptionGraphicsItem* option, QWidget* widget) override {
        ++paints;
        QGraphicsPathItem::paint(painter, option, widget);
    }
};
int CountedPath::paints = 0;

static void flush()
{
    for (int i = 0; i < 5; ++i) {
        QApplication::sendPostedEvents();
        QApplication::processEvents();
    }
}

static QImage screen(QGVPage& view)
{
    return view.viewport()->grab().toImage();
}

static QImage exportImage(QGraphicsScene& scene)
{
    QImage result(600, 400, QImage::Format_ARGB32_Premultiplied);
    result.fill(Qt::white);
    QPainter painter(&result);
    painter.setRenderHint(QPainter::Antialiasing);
    scene.render(&painter, QRectF(0, 0, 600, 400), QRectF(0, 0, 600, 400));
    return result;
}

static QByteArray exportSvg(QGraphicsScene& scene)
{
    QByteArray result;
    QBuffer buffer(&result);
    buffer.open(QIODevice::WriteOnly);
    QSvgGenerator generator;
    generator.setOutputDevice(&buffer);
    generator.setSize(QSize(600, 400));
    generator.setViewBox(QRect(0, 0, 600, 400));
    QPainter painter(&generator);
    scene.render(&painter, QRectF(0, 0, 600, 400), QRectF(0, 0, 600, 400));
    painter.end();
    return result;
}

static void partialUpdateChecks()
{
    QGraphicsScene scene;
    scene.setSceneRect(0, 0, 1500, 1000);
    CountedPath* target = nullptr;
    for (int y = 0; y < 40; ++y) {
        for (int x = 0; x < 60; ++x) {
            auto* item = new CountedPath;
            QPainterPath path;
            path.moveTo(0, 0);
            path.lineTo(12, 6);
            item->setPath(path);
            item->setPos(x * 18, y * 15);
            scene.addItem(item);
            if (x == 15 && y == 15) target = item;
        }
    }
    QGVPage view(&scene);
    view.resize(640, 480);
    view.setBackgroundBrush(Qt::white);
    view.show();
    view.centerOn(300, 220);
    flush();
    view.setViewportUpdateMode(QGraphicsView::FullViewportUpdate);
    flush();
    CountedPath::paints = 0;
    target->setPen(QPen(Qt::red, 1));
    flush();
    const auto fullPaints = CountedPath::paints;
    view.setViewportUpdateMode(QGraphicsView::MinimalViewportUpdate);
    flush();
    CountedPath::paints = 0;
    target->setPen(QPen(Qt::blue, 1));
    flush();
    const auto partialPaints = CountedPath::paints;
    CHECK(partialPaints > 0 && partialPaints < fullPaints / 4);
    std::cout << "MICROBENCH local color update 2400 paths: full_paints=" << fullPaints
              << " partial_paints=" << partialPaints << '\n';
    const auto partial = screen(view);
    view.setViewportUpdateMode(QGraphicsView::FullViewportUpdate);
    flush();
    CHECK(screen(view) == partial);
}

void navigationChecks()
{
    partialUpdateChecks();
    {
        QGraphicsScene empty;
        empty.setSceneRect(-1000, -1000, 2000, 2000);
        QGVPage updated(&empty);
        OriginalBackgroundPage original(&empty);
        updated.resize(320, 240);
        original.resize(320, 240);
        updated.show(); original.show(); flush();
        for (const QColor& color : {QColor(Qt::white), QColor(Qt::gray), QColor(42, 96, 135), QColor(112, 112, 112, 0), QColor(80, 90, 100, 128)}) {
            updated.background.setColor(color);
            original.background.setColor(color);
            updated.resetCachedContent();
            original.resetCachedContent();
            for (double scale : {0.6, 1.0, 1.25, 2.0}) {
                updated.setTransform(QTransform().rotate(7).scale(scale, scale));
                original.setTransform(updated.transform());
                CHECK(screen(updated) == screen(original));
            }
        }
    }
    CHECK(NavigationPreview::rasterSize(QSize(4096, 4096), 1) == QSize(4096, 4096));
    CHECK(NavigationPreview::rasterSize(QSize(4097, 4096), 1).isEmpty());
    CHECK(NavigationPreview::rasterSize(QSize(4096, 4096), 2).isEmpty());
    CHECK(NavigationPreview::rasterSize(QSize(101, 99), 1.25) == QSize(127, 124));
    CHECK(NavigationPreview::rasterSize(QSize(1, 1), 0).isEmpty());
    CHECK(NavigationPreview::rasterSize(QSize(1, 1), std::numeric_limits<double>::quiet_NaN()).isEmpty());
    CHECK(NavigationPreview::rasterSize(QSize(1, 1), std::numeric_limits<double>::infinity()).isEmpty());
    QGraphicsScene scene;
    scene.setSceneRect(-1000, -1000, 3000, 3000);
    CountedPath* target = nullptr;
    for (int y = -10; y < 30; ++y) {
        for (int x = -10; x < 40; ++x) {
            auto* item = new CountedPath;
            QPainterPath path;
            path.moveTo(0, 0);
            path.cubicTo(8, -4, 4, 9, 12, 6);
            item->setPath(path);
            item->setPen(QPen(Qt::black, 0.6));
            item->setPos(x * 18, y * 15);
            item->setFlag(QGraphicsItem::ItemIsSelectable);
            scene.addItem(item);
            if (x == 10 && y == 10) target = item;
        }
    }
    auto* text = scene.addText("Dimension 42.000 mm");
    text->setPos(180, 120);
    QGVPage view(&scene);
    view.setRenderHint(QPainter::Antialiasing);
    view.setBackgroundBrush(Qt::white);
    view.setViewportUpdateMode(QGraphicsView::FullViewportUpdate);
    view.resize(639, 479);
    view.show();
    view.centerOn(250, 180);
    flush();
    auto& cache = *view.m_navigationPreview;
    for (const QColor& color : {QColor(112, 112, 112, 0), QColor(80, 90, 100, 128)}) {
        view.background.setColor(color);
        view.resetCachedContent();
        view.viewport()->update();
        flush();
        const auto reference = screen(view);
        CHECK(cache.begin());
        const auto preview = screen(view);
        CHECK(reference.size() == preview.size());
        int alphaError = 0, outsideTextError = 0;
        const QRectF labelPixels = view.mapFromScene(text->sceneBoundingRect()).boundingRect();
        for (int y = 0; y < reference.height(); ++y) {
            for (int x = 0; x < reference.width(); ++x) {
                const QColor a = reference.pixelColor(x, y), b = preview.pixelColor(x, y);
                const int error = std::max({std::abs(a.red() - b.red()),
                                            std::abs(a.green() - b.green()), std::abs(a.blue() - b.blue())});
                alphaError = std::max(alphaError, error);
                if (!labelPixels.adjusted(-2, -2, 2, 2).contains(QPointF(x, y) / view.devicePixelRatioF()))
                    outsideTextError = std::max(outsideTextError, error);
            }
        }
        std::cout << "ALPHA dpr=" << view.devicePixelRatioF() << " alpha=" << color.alpha()
                  << " max_error=" << alphaError << " outside_text_error=" << outsideTextError << " logical_dpi=" << view.viewport()->logicalDpiX() << '\n';
        if (alphaError > 4) {
            reference.save("/tmp/techdraw-alpha-reference.png");
            preview.save("/tmp/techdraw-alpha-preview.png");
        }
        CHECK(alphaError <= 4);
        cache.invalidate();
    }
    view.background.setColor(Qt::white);
    view.resetCachedContent();
    view.viewport()->update();
    flush();
    const auto originalShape = target->shape();
    const auto originalPos = target->pos();
    const auto exported = exportImage(scene);
    const auto svg = exportSvg(scene);
    const auto initial = screen(view);
    QElapsedTimer capture;
    capture.start();
    CHECK(cache.begin());
    const auto captureNs = capture.nsecsElapsed();
    const auto previewInitial = screen(view);
    CHECK(previewInitial.size() == initial.size());
    // QGraphicsView::render and QWidget paint differ slightly in antialias rounding.
    // No displacement is allowed; rounding is <=2/255 at DPR=1 and <=4/255 at DPR=1.5.
    int maxError = 0;
    for (int y = 0; y < initial.height(); ++y) {
        for (int x = 0; x < initial.width(); ++x) {
            QColor a = initial.pixelColor(x, y), b = previewInitial.pixelColor(x, y);
            maxError = std::max({maxError, std::abs(a.red() - b.red()),
                                std::abs(a.green() - b.green()), std::abs(a.blue() - b.blue())});
        }
    }
    std::cout << "PREVIEW initial raster max_channel_error=" << maxError
              << " dpr=" << view.devicePixelRatioF() << '\n';
    CHECK(maxError <= 4);
    CHECK(cache.bytes() > 0 && cache.bytes() <= NavigationPreview::maxBytes);
    // A screen preview never changes scene exports or hit-test geometry.
    CHECK(exportImage(scene) == exported);
    CHECK(exportSvg(scene) == svg);
    CHECK(target->shape() == originalShape && target->pos() == originalPos);
    CHECK(scene.items(target->mapToScene(QPointF(0, 0))).contains(target));
    CountedPath::paints = 0;
    QElapsedTimer timer;
    timer.start();
    for (int i = 0; i < 20; ++i) {
        CHECK(cache.begin());
        const auto beforePaint = CountedPath::paints;
        view.setTransform(QTransform::fromScale(i % 2 ? 1.04 : 1.02, i % 2 ? 1.04 : 1.02));
        screen(view);
        CHECK(CountedPath::paints == beforePaint);
        // A slow/instrumented event loop may legitimately exceed the 120 ms idle
        // deadline and perform an exact paint here. Count it, do not suppress it.
        flush();
    }
    const auto previewNs = timer.nsecsElapsed();
    const auto previewExtraPaints = CountedPath::paints;
    cache.invalidate();
    timer.restart();
    screen(view);
    flush();
    const auto finalFrameNs = timer.nsecsElapsed();
    CountedPath::paints = 0;
    timer.restart();
    for (int i = 0; i < 20; ++i) {
        view.setTransform(QTransform::fromScale(i % 2 ? 1.04 : 1.02, i % 2 ? 1.04 : 1.02));
        screen(view);
        flush();
    }
    const auto exactNs = timer.nsecsElapsed();
    CHECK(CountedPath::paints > 0);
    std::cout << "MICROBENCH navigation 2000 paths, 20 zoom steps: exact_ns=" << exactNs
              << " initial_capture_ns=" << captureNs << " preview_ns=" << previewNs << " final_exact_ns=" << finalFrameNs << " preview_extra_paints=" << previewExtraPaints << " vector_paints=" << CountedPath::paints << '\n';

    const auto exact = screen(view);
    CHECK(cache.begin());
    QEventLoop idle;
    QTimer::singleShot(170, &idle, &QEventLoop::quit);
    idle.exec();
    CHECK(!cache.active());
    CHECK(screen(view) == exact);

    // Panning inside the reserve reuses the raster; exact final image matches a fresh draw.
    CHECK(cache.begin());
    CountedPath::paints = 0;
    view.horizontalScrollBar()->setValue(view.horizontalScrollBar()->value() + 20);
    screen(view);
    CHECK(CountedPath::paints == 0);
    cache.invalidate();
    const auto panned = screen(view);
    view.viewport()->update();
    flush();
    CHECK(screen(view) == panned);

    // Immediate selection notification and queued changes both invalidate the preview.
    CHECK(cache.begin());
    target->setSelected(true);
    CHECK(!cache.active());
    CHECK(target->isSelected() && target->shape() == originalShape);
    flush();
    CHECK(cache.begin());
    target->setPos(300, 100);
    text->setPlainText("Dimension 43.000 mm");
    flush();
    CHECK(!cache.active());
    CHECK(cache.begin());
    target->hide();
    flush();
    CHECK(!cache.active());
    CHECK(cache.begin());
    delete target;
    target = nullptr;
    flush();
    CHECK(!cache.active());

    CHECK(cache.begin());
    view.scale(0.1, 0.1); // outside cache coverage: no blank/stale border is permitted
    screen(view);
    CHECK(!cache.active());
    view.resetTransform();
    flush();
    CHECK(cache.begin());
    view.resize(700, 500);
    screen(view);
    CHECK(!cache.active());
    flush();
    CHECK(cache.begin());
    view.setRenderHint(QPainter::Antialiasing, false);
    screen(view);
    CHECK(!cache.active());
    // Renderer switches and opt-in controls use actual QGVPage methods.
    auto* prefs = Preferences::getPreferenceGroup("General");
    view.setRenderer(QGVPage::RendererType::Native);
    CHECK(view.viewportUpdateMode() == QGraphicsView::FullViewportUpdate);
    view.beginNavigationPreview();
    CHECK(!cache.active());
    prefs->partial = true;
    view.setRenderer(QGVPage::RendererType::Native);
    CHECK(view.viewportUpdateMode() == QGraphicsView::MinimalViewportUpdate);
    flush();
    prefs->preview = true;
    view.toolHandler = true;
    view.beginNavigationPreview();
    CHECK(!cache.active());
    view.toolHandler = false;
    view.balloonPlacing = true;
    view.beginNavigationPreview();
    CHECK(!cache.active());
    view.balloonPlacing = false;
    view.beginNavigationPreview();
    CHECK(cache.active());
    cache.invalidate();
    QGVNavStyle navigation(&view);
    navigation.zoom(1.0);
    CHECK(!cache.active());
    navigation.zoom(1.02);
    CHECK(cache.active());
    cache.invalidate();
    navigation.pan(QPoint(5, 5));
    CHECK(cache.active());
    view.setRenderer(QGVPage::RendererType::Image);
    CHECK(!cache.active());
    CHECK(view.viewportUpdateMode() == QGraphicsView::FullViewportUpdate);
    view.beginNavigationPreview();
    CHECK(!cache.active());
    view.setRenderer(QGVPage::RendererType::Native);
    flush();
    view.hide();
    CHECK(!cache.begin());
    prefs->partial = prefs->preview = false;
    {
        auto* ephemeral = new QGraphicsScene;
        ephemeral->addRect(0, 0, 100, 100);
        QGVPage lifetime(ephemeral);
        lifetime.show(); flush();
        CHECK(lifetime.m_navigationPreview->begin());
        delete ephemeral;
        CHECK(!lifetime.m_navigationPreview->active());
    }
    std::cout << "PASS navigation: cache reuse, exact idle image, pan, geometry, vector export, invalidation\n";
}
