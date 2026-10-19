// SPDX-License-Identifier: LGPL-2.1-or-later
// Narrow fixtures compile the ACTUAL patched methods without FreeCAD/OCCT linkage.
// They do not stand in for a complete FreeCAD dimension interaction test.
#include <QGraphicsPathItem>
#include <QPainterPathStroker>
#include <iostream>
#include <stdexcept>
#include "EdgeGeometryCache.h"

class QGIEdge : public QGraphicsPathItem
{
public:
    double fuzz{10};
    double getEdgeFuzz() const { return fuzz; }
    QRectF boundingRect() const override;
    QPainterPath shape() const override;
private:
    TechDrawGui::EdgeGeometryCache m_geometryCache;
};

class ColoredPath : public QGraphicsPathItem
{
public:
    explicit ColoredPath(QGraphicsItem* parent) : QGraphicsPathItem(parent) {}
    int appearance{-1};
    void setPrettyNormal() { appearance = 0; }
    void setPrettyPre() { appearance = 1; }
    void setPrettySel() { appearance = 2; }
};

class QGIViewDimension : public QGraphicsRectItem
{
public:
    QGIViewDimension()
    {
        datumLabel = new ColoredPath(this);
        dimLines = new ColoredPath(this);
        aHead1 = new ColoredPath(this);
        aHead2 = new ColoredPath(this);
        datumLabel->setFlag(ItemIsSelectable, true);
    }
    void hover(bool state);
    void setPrettyNormal();
    void setPrettyPre();
    void setPrettySel();
    void draw() { throw std::runtime_error("Hover must not rebuild dimension geometry"); }
    bool hasHover{false};
    ColoredPath *datumLabel, *dimLines, *aHead1, *aHead2;
};

#include "patched_methods.inc"

void integrationChecks()
{
    QGIEdge edge;
    QGraphicsPathItem* base = &edge;
    QPainterPath path;
    path.moveTo(-2, 1);
    path.cubicTo(30, 12, -5, -7, 20, 40);
    for (int i = 0; i < 10; ++i) {
        base->setPath(path);
        edge.fuzz = i + 0.5;
        QPainterPathStroker reference;
        reference.setWidth(edge.fuzz);
        auto shape = reference.createStroke(path);
        if (edge.shape() != shape || edge.boundingRect() != shape.controlPointRect()) {
            throw std::runtime_error("Patched QGIEdge methods differ from original geometry");
        }
        path.translate(2, -3);
    }
    QGIViewDimension dimension;
    dimension.dimLines->setPath(path);
    dimension.datumLabel->setPos(20, 35);
    for (bool selected : {false, true}) {
        dimension.datumLabel->setSelected(selected);
        for (bool hover : {true, false, false, true}) {
            dimension.hover(hover);
            const int expected = selected ? 2 : hover ? 1 : 0;
            for (auto* child : {dimension.dimLines, dimension.aHead1, dimension.aHead2}) {
                if (child->appearance != expected) throw std::runtime_error("Wrong hover/selection color");
            }
            if (dimension.dimLines->path() != path || dimension.datumLabel->pos() != QPointF(20, 35)) {
                throw std::runtime_error("Hover changed dimension geometry or label position");
            }
        }
    }
    std::cout << "PASS actual patched edge/hover methods in isolated Qt fixtures\n";
}
