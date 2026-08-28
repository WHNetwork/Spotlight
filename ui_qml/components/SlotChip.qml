import QtQuick

Item {
    id: root
    property string label: ""
    property string indexLabel: ""
    property bool completed: false
    property bool current: false
    property real scaleFactor: 1.0

    opacity: completed ? 0.55 : 1.0

    Rectangle {
        anchors.fill: parent
        radius: 12 * root.scaleFactor
        color: root.current ? Qt.rgba(0.90, 0.885, 0.97, 1.0)
             : (root.completed ? Qt.rgba(0.975, 0.975, 0.98, 1.0) : Qt.rgba(0.945, 0.945, 0.965, 1.0))
        border.width: 1
        border.color: root.current ? Qt.rgba(0.62, 0.58, 0.86, 0.85)
             : (root.completed ? Qt.rgba(0.45, 0.5, 0.65, 0.08) : Qt.rgba(0.45, 0.5, 0.65, 0.16))
    }

    Column {
        anchors.centerIn: parent
        spacing: 2 * root.scaleFactor
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.indexLabel
            color: "#9A96B7"
            font.pixelSize: 9 * root.scaleFactor
            font.family: "Microsoft YaHei UI"
        }
        Text {
            anchors.horizontalCenter: parent.horizontalCenter
            text: root.label
            color: root.current ? "#3D4963" : "#68738C"
            font.pixelSize: root.current ? 12.5 * root.scaleFactor : 12 * root.scaleFactor
            font.bold: root.current
            font.family: "Microsoft YaHei UI"
        }
    }

    Text {
        anchors.right: parent.right
        anchors.rightMargin: 6 * root.scaleFactor
        anchors.top: parent.top
        anchors.topMargin: 5 * root.scaleFactor
        text: "当前"
        visible: root.current
        color: "#7A6FA8"
        font.pixelSize: 9 * root.scaleFactor
        font.family: "Microsoft YaHei UI"
    }
}
