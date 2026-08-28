import QtQuick

// A single segmented control (e.g. provider / model tier). Not three pills.
Item {
    id: root
    property var items: []              // [{value, label}, ...]
    property string currentValue: ""
    property real scaleFactor: 1.0
    signal valueSelected(string value)

    implicitHeight: 40 * scaleFactor
    height: implicitHeight

    Rectangle {
        anchors.fill: parent
        radius: 12 * scaleFactor
        color: Qt.rgba(1.0, 0.99, 1.0, 0.16)
        border.width: 1
        border.color: Qt.rgba(1.0, 1.0, 1.0, 0.40)
    }

    Row {
        anchors.fill: parent
        spacing: 0

        Repeater {
            model: root.items
            Item {
                width: root.items.length > 0 ? root.width / root.items.length : 0
                height: root.height
                readonly property bool selected: root.currentValue === modelData.value

                Rectangle {
                    anchors.centerIn: parent
                    width: parent.width - 4 * scaleFactor
                    height: parent.height - 6 * scaleFactor
                    radius: 10 * scaleFactor
                    color: parent.selected ? Qt.rgba(1.0, 1.0, 1.0, 0.55) : "transparent"
                    Behavior on color { ColorAnimation { duration: 150 } }
                }

                Text {
                    anchors.centerIn: parent
                    text: modelData.label
                    color: parent.selected ? "#3D4963" : "#7A7F9C"
                    font.pixelSize: 12 * scaleFactor
                    font.bold: parent.selected
                    font.family: "Microsoft YaHei UI"
                    Behavior on color { ColorAnimation { duration: 150 } }
                }

                HoverHandler { cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: root.valueSelected(modelData.value) }
            }
        }
    }
}
