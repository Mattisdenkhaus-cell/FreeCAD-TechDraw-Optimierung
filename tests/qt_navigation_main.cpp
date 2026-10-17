// SPDX-License-Identifier: LGPL-2.1-or-later
#include <QApplication>
#include <iostream>
#include <stdexcept>
void navigationChecks();
int main(int argc, char** argv)
{
    QApplication app(argc, argv);
    try { navigationChecks(); }
    catch (const std::exception& error) {
        std::cerr << "FAIL: " << error.what() << '\n';
        return 1;
    }
    return 0;
}
