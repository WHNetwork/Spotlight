import QtQuick

Item {
    id: root
    property string label: ""
    property int value: 0
    property bool isBody: true
    property real scaleFactor: 1.0

    implicitHeight: 24 * scaleFactor
    width: parent ? parent.width : 0

    readonly property real labelW: (isBody ? 62 : 44) * scaleFactor

    Text {
        text: root.label
        color: "#68738C"
        font.pixelSize: 11 * scaleFactor
        font.family: "Microsoft YaHei UI"
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        width: root.labelW
        elide: Text.ElideRight
    }
    Rectangle {
        anchors.left: parent.left
        anchors.leftMargin: root.labelW + 8 * root.scaleFactor
        anchors.right: parent.right
        anchors.rightMargin: 38 * root.scaleFactor
        anchors.verticalCenter: parent.verticalCenter
        height: 4 * root.scaleFactor
        radius: 2 * root.scaleFactor
        color: Qt.rgba(0.45, 0.5, 0.62, 0.14)
        Rectangle {
            width: parent.width * Math.max(0, Math.min(1, root.value / 100.0))
            height: parent.height
            radius: parent.radius
            color: root.isBody ? Qt.rgba(0.55, 0.66, 0.86, 0.65) : Qt.rgba(0.62, 0.56, 0.82, 0.65)
        }
    }
    Text {
        text: String(root.value)
        color: "#56617A"
        font.pixelSize: 11 * scaleFactor
        font.family: "Microsoft YaHei UI"
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        width: 30 * scaleFactor
        horizontalAlignment: Text.AlignRight
    }
}
