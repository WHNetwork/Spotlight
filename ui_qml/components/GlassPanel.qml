import QtQuick

Item {
    id: root
    default property alias contentData: content.data

    property real scaleFactor: 1.0
    property real radius: 24 * scaleFactor
    property real padding: 18 * scaleFactor
    property real glassAlpha: 0.40
    property color tintColor: Qt.rgba(0.86, 0.82, 0.95, 0.05)
    property color shadowColor: "#536B89"
    property real shadowAlpha: 0.08

    Rectangle {
        id: shadow
        x: -6 * scaleFactor
        y: 8 * scaleFactor
        width: root.width + 12 * scaleFactor
        height: root.height + 12 * scaleFactor
        radius: root.radius + 6 * scaleFactor
        color: root.shadowColor
        opacity: root.shadowAlpha
    }

    Rectangle {
        id: glass
        anchors.fill: parent
        radius: root.radius
        color: Qt.rgba(1.0, 0.99, 1.0, root.glassAlpha)
        border.width: 1
        border.color: Qt.rgba(1.0, 1.0, 1.0, 0.72)
        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            color: root.tintColor
        }
    }

    Item {
        id: content
        anchors.fill: parent
        anchors.margins: root.padding
    }
}
