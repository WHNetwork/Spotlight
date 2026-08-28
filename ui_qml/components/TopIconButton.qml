import QtQuick

Item {
    id: root
    signal clicked()
    property url iconSource: ""
    property string label: ""
    property bool enabled: true
    property real scaleFactor: 1.0

    implicitWidth: 36 * scaleFactor
    implicitHeight: 34 * scaleFactor
    width: implicitWidth
    height: implicitHeight
    opacity: enabled ? 1.0 : 0.4

    HoverHandler { id: tHover; enabled: root.enabled; cursorShape: Qt.PointingHandCursor }
    TapHandler { id: tTap; enabled: root.enabled; onTapped: if (root.enabled) root.clicked() }

    Rectangle {
        anchors.fill: parent
        radius: 10 * root.scaleFactor
        color: tHover.hovered && root.enabled ? Qt.rgba(0.93, 0.92, 0.97, 1.0) : "transparent"
        Behavior on color { ColorAnimation { duration: 150 } }
        Image {
            anchors.centerIn: parent
            source: root.iconSource
            width: 18 * root.scaleFactor
            height: 18 * root.scaleFactor
            fillMode: Image.PreserveAspectFit
            sourceSize: Qt.size(20 * root.scaleFactor, 20 * root.scaleFactor)
            opacity: 0.85
        }
    }
}
