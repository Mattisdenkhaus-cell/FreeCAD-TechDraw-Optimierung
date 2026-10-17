// SPDX-License-Identifier: LGPL-2.1-or-later
// Compile the actual QGIFace::buildSvgHatch body in both A/B modes. Only the
// unrelated FreeCAD preference/console/model layer is replaced by this fixture.
#include <QGraphicsPathItem>
#include <QSvgRenderer>
#include <cmath>
#include <limits>
#include <iostream>
#include <stdexcept>
#include "QGIBatchedSvgHatch.h"
#include "QGCustomSvg.h"
using namespace TechDrawGui;

namespace Base {
struct TestConsole {
    template<class... Args> void warning(const char*, Args...) {}
    template<class... Args> void message(const char*, Args...) {}
};
inline TestConsole& Console() { static TestConsole console; return console; }
}
struct Preferences { static double svgHatchFactor() { return 2; } };

class QGIFace : public QGraphicsPathItem
{
public:
    QGIFace()
    {
#include "hatch_constructor.inc"
        m_svgHatchArea->setParentItem(this);
        m_sharedRender = new QSvgRenderer();
    }
    ~QGIFace() override { delete m_sharedRender; }
    void buildSvgHatch();
    struct Offset { double x{0}, y{0}; };
    Offset getHatchOffset() const { return {}; }
    constexpr static int SVGSIZEW = 64;
    constexpr static int SVGSIZEH = 64;
    double m_fillScale{1};
    double m_hatchRotation{0};
    long m_maxTile{3};
    QGCustomRect* m_svgHatchArea{};
    QSvgRenderer* m_sharedRender{};
    std::string SVGCOLPREFIX{"stroke=\""}, SVGCOLDEFAULT{"#000000"}, m_svgCol{"#ff0000"};
    QByteArray m_svgXML{R"(<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><path stroke="#000000" d="M0 0 L64 64"/></svg>)"};
};

#include "hatch_method.inc"

void hatchIntegrationChecks()
{
    QGIFace face;
    QPainterPath path;
    path.addRect(QRectF(-100, -100, 200, 200));
    face.setPath(path);
    face.buildSvgHatch();
    const auto position = face.m_svgHatchArea->pos();
    for (int i = 0; i < 4; ++i) {
        face.buildSvgHatch();
        if (face.m_svgHatchArea->pos() != position) throw std::runtime_error("Hatch drifts on rebuild");
#if TECHDRAW_BATCH_SVG_HATCH
        if (!face.m_svgHatchArea->childItems().isEmpty()) throw std::runtime_error("Batched hatch allocated child tiles");
#else
        if (face.m_svgHatchArea->childItems().size() != 4) throw std::runtime_error("Original hatch accumulates child tiles");
#endif
    }
    face.m_fillScale = 0;
    face.buildSvgHatch();
#if TECHDRAW_BATCH_SVG_HATCH
    int count = 0;
    static_cast<QGIBatchedSvgHatch*>(face.m_svgHatchArea)->forEachVisibleTile(
        QRectF(-1000, -1000, 2000, 2000), [&](QPointF) { ++count; });
    if (count) throw std::runtime_error("Invalid scale kept cached tiles");
#else
    if (!face.m_svgHatchArea->childItems().isEmpty()) throw std::runtime_error("Invalid scale kept child tiles");
#endif
    std::cout << "PASS actual hatch constructor allocation and buildSvgHatch, mode=" << TECHDRAW_BATCH_SVG_HATCH << '\n';
}
