import QtQuick

Item {
    id: root
    default property alias contentData: content.data

    property real glassAlpha: 0.40
    property real radius: 20

    Rectangle {
        id: glass
        anchors.fill: parent
        radius: root.radius
        color: Qt.rgba(1.0, 1.0, 1.0, 1.0)
        border.width: 1
        border.color: Qt.rgba(0.45, 0.5, 0.65, 0.12)
        clip: true

        Rectangle {
            anchors.fill: parent
            color: Qt.rgba(0.88, 0.84, 0.97, 0.04)
        }

        Item {
            id: content
            anchors.fill: parent
        }
    }
}
