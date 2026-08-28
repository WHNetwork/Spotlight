import QtQuick

Item {
    id: root
    property string label: ""
    property string valueText: ""
    property bool muted: false
    property real scaleFactor: 1.0

    implicitHeight: 26 * scaleFactor
    width: parent ? parent.width : 0

    Text {
        text: root.label
        color: root.muted ? "#9A96B7" : "#68738C"
        font.pixelSize: 12 * root.scaleFactor
        font.family: "Microsoft YaHei UI"
        anchors.left: parent.left
        anchors.verticalCenter: parent.verticalCenter
        width: parent.width * 0.62
        elide: Text.ElideRight
    }
    Text {
        text: root.valueText
        color: root.muted ? "#9A96B7" : "#3D4963"
        font.pixelSize: 12 * root.scaleFactor
        font.bold: !root.muted
        font.family: "Microsoft YaHei UI"
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
    }
}
