import QtQuick

Item {
    id: root
    signal clicked()
    property string label: ""
    property bool selected: false
    property real scaleFactor: 1.0

    implicitWidth: chipText.implicitWidth + 30 * scaleFactor
    implicitHeight: 34 * scaleFactor
    width: implicitWidth
    height: implicitHeight

    HoverHandler { id: chipHover; cursorShape: Qt.PointingHandCursor }
    TapHandler { id: chipTap; onTapped: root.clicked() }

    Rectangle {
        anchors.fill: parent
        radius: 11 * root.scaleFactor
        color: root.selected ? Qt.rgba(0.86, 0.83, 0.95, 1.0)
             : (chipHover.hovered ? Qt.rgba(0.91, 0.90, 0.96, 1.0) : Qt.rgba(0.955, 0.95, 0.975, 1.0))
        border.width: 1
        border.color: root.selected ? Qt.rgba(0.62, 0.58, 0.86, 0.85)
             : (chipHover.hovered ? Qt.rgba(0.55, 0.55, 0.72, 0.35) : Qt.rgba(0.5, 0.52, 0.68, 0.18))
        Behavior on color { ColorAnimation { duration: 150 } }
        Behavior on border.color { ColorAnimation { duration: 150 } }
    }

    Text {
        id: chipText
        anchors.centerIn: parent
        text: root.label
        color: root.selected ? "#3D4963" : "#4C5670"
        font.pixelSize: 12 * root.scaleFactor
        font.family: "Microsoft YaHei UI"
    }
}
