import QtQuick
import QtQuick.Controls

// Labeled popup selector for many-option fields (nationality / MBTI / identity).
// Same glass field look as GlassInput; options open in a small scrollable popup.
Item {
    id: root
    property string label: ""
    property string value: ""
    property var options: []
    property real scaleFactor: 1.0
    signal valueSelected(string value)

    readonly property real labelH: 16 * scaleFactor
    readonly property real fieldH: 40 * scaleFactor

    implicitWidth: 240 * scaleFactor
    implicitHeight: labelH + 4 * scaleFactor + fieldH
    width: implicitWidth
    height: implicitHeight

    Column {
        anchors.fill: parent
        spacing: 4 * scaleFactor

        Text {
            text: root.label
            color: "#68738C"
            font.pixelSize: 11 * scaleFactor
            font.family: "Microsoft YaHei UI"
        }

        Item {
            width: parent.width
            height: root.fieldH

            Rectangle {
                id: bg
                anchors.fill: parent
                radius: 12 * scaleFactor
                color: Qt.rgba(1.0, 1.0, 1.0, 0.22)
                border.width: 1
                border.color: Qt.rgba(1.0, 1.0, 1.0, 0.50)
                Behavior on color { ColorAnimation { duration: 120 } }
                Behavior on border.color { ColorAnimation { duration: 120 } }
            }

            Row {
                anchors.fill: parent
                anchors.leftMargin: 12 * scaleFactor
                anchors.rightMargin: 10 * scaleFactor
                spacing: 6 * scaleFactor

                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: root.value !== "" ? root.value : "请选择"
                    color: root.value !== "" ? "#46536D" : "#8A92A8"
                    font.pixelSize: 13 * scaleFactor
                    font.family: "Microsoft YaHei UI"
                    elide: Text.ElideRight
                    width: parent.width - 18 * scaleFactor
                }
                Text {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "⌄"
                    color: "#7A7F9C"
                    font.pixelSize: 14 * scaleFactor
                    font.family: "Microsoft YaHei UI"
                }
            }

            HoverHandler { cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: popup.open() }
        }
    }

    Popup {
        id: popup
        parent: root
        x: 0
        y: root.height + 2 * scaleFactor
        width: root.width + 24 * scaleFactor
        implicitHeight: listView.height
        padding: 0
        modal: true
        closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside

        background: Rectangle {
            radius: 14 * scaleFactor
            color: Qt.rgba(0.985, 0.98, 1.0, 0.96)
            border.width: 1
            border.color: Qt.rgba(0.98, 0.97, 1.0, 0.85)
            layer.enabled: true
        }

        contentItem: ListView {
            id: listView
            width: popup.width
            height: Math.min(root.options.length * 40 * scaleFactor + 12 * scaleFactor, 384 * scaleFactor)
            clip: true
            boundsBehavior: Flickable.StopAtBounds
            model: root.options
            delegate: ItemDelegate {
                width: popup.width
                height: 40 * scaleFactor
                padding: 0
                highlighted: false
                background: Rectangle {
                    radius: 10 * scaleFactor
                    color: rowHover.hovered ? Qt.rgba(1.0, 1.0, 1.0, 0.65) : "transparent"
                }
                contentItem: Item {
                    Text {
                        anchors.left: parent.left
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.leftMargin: 14 * scaleFactor
                        text: modelData
                        color: modelData === root.value ? "#3D4963" : "#46536D"
                        font.pixelSize: 13 * scaleFactor
                        font.bold: modelData === root.value
                        font.family: "Microsoft YaHei UI"
                    }
                    Text {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        anchors.rightMargin: 12 * scaleFactor
                        text: modelData === root.value ? "✓" : ""
                        color: "#3D4963"
                        font.pixelSize: 13 * scaleFactor
                    }
                }
                HoverHandler { id: rowHover; cursorShape: Qt.PointingHandCursor }
                onClicked: {
                    root.value = modelData
                    root.valueSelected(modelData)
                    popup.close()
                }
            }
        }
    }
}
