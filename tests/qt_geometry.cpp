// SPDX-License-Identifier: LGPL-2.1-or-later
#include <QApplication>
#include <QElapsedTimer>
#include <QGraphicsPathItem>
#include <QGraphicsScene>
#include <QImage>
#include <QPainter>
#include <QRandomGenerator>
#include <QSvgRenderer>
#include <QTransform>
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>
#include "EdgeGeometryCache.h"
#include "QGIBatchedSvgHatch.h"
#include "QGCustomSvg.h"

using namespace TechDrawGui;
#define CHECK(expr) do { if (!(expr)) throw std::runtime_error(#expr); } while (false)

static QPainterPath referenceShape(const QPainterPath& path, qreal fuzz)
{
    QPainterPathStroker stroker;
    stroker.setWidth(fuzz);
    return stroker.createStroke(path);
}

static void edgeGeometry()
{
    EdgeGeometryCache cache;
    QGraphicsPathItem item;
    QPainterPath path;
    for (int k = 0; k < 15; ++k) {
        path.cubicTo(k + 5, k * 4, k + 9, -k * 3, k + 12, k + 2);
    }
    for (int change = 0; change < 5; ++change) {
        if (change == 1) path.translate(23, -14);
        if (change == 2) path.setElementPositionAt(1, 8, -12);
        if (change == 3) path.setFillRule(Qt::WindingFill);
        if (change == 4) path = QPainterPath();
        item.setPath(path); // deliberately through the Qt base API
        for (double fuzz : {10., 0., -1., 0.1, 30., 10.}) {
            const auto reference = referenceShape(item.path(), fuzz);
            for (int repeat = 0; repeat < 4; ++repeat) {
                CHECK(cache.shape(item.path(), fuzz) == reference);
                CHECK(cache.bounds(item.path(), fuzz) == reference.controlPointRect());
            }
            for (int x = -10; x < 40; ++x) {
                CHECK(cache.shape(item.path(), fuzz).contains(QPointF(x, 2)) ==
                      reference.contains(QPointF(x, 2)));
            }
        }
    }
    // A cache snapshot must detach when the caller changes a shared path.
    item.setPath(QPainterPath(QPointF(1, 2)));
    cache.shape(item.path(), 10);
    path = item.path();
    path.lineTo(30, 40);
    item.setPath(path);
    CHECK(cache.shape(item.path(), 10) == referenceShape(item.path(), 10));
    std::cout << "PASS edge geometry, selection, empty path, base setter, fuzz and detach\n";
}

static void mappedBounds()
{
    QGraphicsRectItem parent;
    QGraphicsRectItem child(&parent);
    child.setRect(-25, 3, 40, 70);
    for (int i = 0; i < 90; ++i) {
        QTransform transform;
        transform.rotate(i * 7);
        transform.shear(i * 0.03, -i * 0.01);
        transform.scale(0.3 + i * 0.1, 2.3);
        child.setTransform(transform);
        child.setPos(-i, 2 * i);
        const auto before = parent.mapFromItem(&child, child.boundingRect()).boundingRect();
        const auto after = parent.mapRectFromItem(&child, child.boundingRect());
        CHECK(std::abs(before.x() - after.x()) < 1e-9);
        CHECK(std::abs(before.y() - after.y()) < 1e-9);
        CHECK(std::abs(before.width() - after.width()) < 1e-9);
        CHECK(std::abs(before.height() - after.height()) < 1e-9);
    }
    std::cout << "PASS mapped bounds: 90 rotations/scales/shears\n";
}

static const QByteArray svg = R"SVG(<svg xmlns="http://www.w3.org/2000/svg" width="8" height="13" viewBox="0 0 8 13"><path d="M0 0 L8 13 M0 6 L4 13" stroke="black" stroke-width="0.7" fill="none"/><circle cx="4" cy="3" r="1.4" fill="red"/></svg>)SVG";

static void tileRanges()
{
    QSvgRenderer renderer(svg);
    CHECK(renderer.isValid());
    QGIBatchedSvgHatch batch;
    QRandomGenerator random(71829);
    for (int trial = 0; trial < 400; ++trial) {
        const int columns = 1 + random.bounded(20);
        const int rows = 1 + random.bounded(20);
        const long limit = random.bounded(300) - 1;
        const qreal scale = 0.2 + random.generateDouble() * 3;
        const qreal dx = 1 + random.generateDouble() * 15;
        const qreal dy = 1 + random.generateDouble() * 15;
        const QPointF origin(-17.3, -24.7);
        batch.configureTiles(&renderer, columns, rows, dx, dy, origin, scale, limit);
        const QRectF exposed(-45 + random.generateDouble() * 200,
                             -45 + random.generateDouble() * 200,
                             1 + random.generateDouble() * 80,
                             1 + random.generateDouble() * 80);
        std::vector<QPointF> expected, actual;
        long count = 0;
        for (int x = 0; x < columns; ++x) {
            for (int y = 0; y < rows; ++y) {
                QPointF p(origin.x() + x * dx, origin.y() + y * dy);
                const QRectF tile(p, QSizeF(8 * scale, 13 * scale));
                CHECK(batch.boundingRect().adjusted(-1e-9, -1e-9, 1e-9, 1e-9).contains(tile));
                if (tile.intersects(exposed)) expected.push_back(p);
                if (++count > limit) break;
            }
            if (count > limit) break;
        }
        batch.forEachVisibleTile(exposed, [&](QPointF p) { actual.push_back(p); });
        CHECK(actual == expected);
    }
    batch.configureTiles(&renderer, 100000000, 100000000, 10, 10, QPointF(), 1,
                         std::numeric_limits<long>::max());
    int visible = 0;
    batch.forEachVisibleTile(QRectF(500, 500, 20, 20), [&](QPointF) { ++visible; });
    CHECK(visible == 6); // 2 columns x 3 overlapping rows; never enumerate 10^16 tiles
    batch.resetTiles();
    visible = 0;
    batch.forEachVisibleTile(QRectF(-1, -1, 100, 100), [&](QPointF) { ++visible; });
    CHECK(visible == 0);
    batch.configureTiles(&renderer, 2, 3, 0, 10, QPointF(), 1, 100);
    batch.forEachVisibleTile(QRectF(-1, -1, 100, 100), [&](QPointF) { ++visible; });
    CHECK(visible == 0);
    std::cout << "PASS SVG ranges: 400 reference grids, limits, reset, invalid size, huge grid\n";
}

static QImage renderScene(bool batched, double rotation, double scale, int limit,
                          const QByteArray& data, const QRectF& sourceRect)
{
    QSvgRenderer renderer(data); // outlives the scene, matching shared-renderer ownership
    CHECK(renderer.isValid());
    QGraphicsScene scene;
    QPainterPath outline;
    outline.addEllipse(QRectF(-40, -25, 80, 50));
    outline.addRect(QRectF(-10, -8, 20, 16)); // hole, clipped using odd-even fill
    auto* face = scene.addPath(outline, QPen(Qt::NoPen), QBrush(Qt::NoBrush));
    face->setFlag(QGraphicsItem::ItemClipsChildrenToShape, true);
    QGCustomRect* area = batched ? static_cast<QGCustomRect*>(new QGIBatchedSvgHatch())
                                : new QGCustomRect();
    area->setParentItem(face);
    area->setRect(0, 0, 90, -90);
    area->centerAt(QPointF());
    const QPointF positionBefore = area->pos();
    const QPointF offset(-4.5, -88.3);
    if (batched) {
        auto* batch = static_cast<QGIBatchedSvgHatch*>(area);
        batch->configureTiles(&renderer, 20, 20, 8 * scale, 13 * scale, offset, scale, limit);
        batch->centerAt(QPointF());
        CHECK(batch->pos() == positionBefore);
    } else {
        int count = 0;
        for (int x = 0; x < 20; ++x) {
            for (int y = 0; y < 20; ++y) {
                auto* tile = new QGCustomSvg();
                tile->setSharedRenderer(&renderer);
                tile->setParentItem(area);
                tile->setScale(scale);
                tile->setPos(offset + QPointF(x * 8 * scale, y * 13 * scale));
                if (++count > limit) break;
            }
            if (count > limit) break;
        }
    }
    area->setTransformOriginPoint(area->mapFromParent(QPointF()));
    area->setRotation(rotation);
    QImage image(480, 320, QImage::Format_ARGB32_Premultiplied);
    image.fill(Qt::white);
    QPainter painter(&image);
    painter.setRenderHint(QPainter::Antialiasing);
    scene.render(&painter, QRectF(0, 0, 480, 320), sourceRect);
    painter.end();
    return image;
}

static void svgPixels()
{
    int images = 0;
    for (double rotation : {0., 23., 90.}) {
        for (double scale : {0.7, 1., 2.}) {
            for (int limit : {0, 17, 150, 1000}) {
                for (const QRectF source : {QRectF(-60, -40, 120, 80), QRectF(-12, -10, 24, 20)}) {
                    auto reference = renderScene(false, rotation, scale, limit, svg, source);
                    auto optimized = renderScene(true, rotation, scale, limit, svg, source);
                    if (reference != optimized) {
                        reference.save("/tmp/techdraw-reference.png");
                        optimized.save("/tmp/techdraw-optimized.png");
                        throw std::runtime_error("SVG pixels differ: rotation=" + std::to_string(rotation) +
                            " scale=" + std::to_string(scale) + " limit=" + std::to_string(limit));
                    }
                    ++images;
                }
            }
        }
    }
    QGIBatchedSvgHatch batch;
    auto* renderer = new QSvgRenderer(svg);
    batch.configureTiles(renderer, 2, 2, 8, 13, QPointF(), 1, 10);
    delete renderer;
    QImage image(40, 40, QImage::Format_ARGB32_Premultiplied);
    image.fill(Qt::white);
    QPainter painter(&image);
    QStyleOptionGraphicsItem option;
    batch.paint(&painter, &option); // guarded renderer, no use-after-free
    std::cout << "PASS SVG pixel equivalence: " << images << " scenes; renderer lifetime\n";
}

static void microbenchmark()
{
    QPainterPath path;
    for (int i = 0; i < 30; ++i) path.cubicTo(i, 4, i + 2, -4, i + 5, 3);
    EdgeGeometryCache cache;
    cache.bounds(path, 10);
    constexpr int iterations = 20000;
    double sink = 0;
    QElapsedTimer timer;
    timer.start();
    for (int i = 0; i < iterations; ++i) sink += referenceShape(path, 10).controlPointRect().width();
    const auto original = timer.nsecsElapsed();
    timer.restart();
    for (int i = 0; i < iterations; ++i) sink += cache.bounds(path, 10).width();
    const auto cached = timer.nsecsElapsed();
    std::cout << "MICROBENCH edge_bounds iterations=" << iterations << " original_ns=" << original
              << " cached_ns=" << cached << " checksum=" << sink << '\n';
}

int main(int argc, char** argv)
{
    QApplication app(argc, argv);
    try {
        edgeGeometry(); mappedBounds(); tileRanges(); svgPixels(); microbenchmark();
    } catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
