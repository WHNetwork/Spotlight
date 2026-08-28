import QtQuick
import QtQuick.Controls

// Labeled glass input field with medium radius (not a pill). Optional password
// reveal that only ever shows the user's *current input*, never a stored key.
Item {
    id: root
    property string label: ""
    property string text: ""
    property string placeholder: ""
    property bool password: false
    property bool revealable: false
    property bool multiline: false
    property string unit: ""
    property real scaleFactor: 1.0
    signal textEdited(string value)

    readonly property real labelH: 16 * scaleFactor
    readonly property real fieldH: (root.multiline ? 84 : 40) * scaleFactor

    implicitHeight: labelH + 4 * scaleFactor + fieldH
    height: implicitHeight

    readonly property bool _revealed: revealBtn._on

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
                color: Qt.rgba(1.0, 1.0, 1.0, field.activeFocus ? 0.34 : 0.22)
                border.width: 1
                border.color: field.activeFocus ? "#9A8FC4" : Qt.rgba(1.0, 1.0, 1.0, 0.50)
                Behavior on color { ColorAnimation { duration: 150 } }
                Behavior on border.color { ColorAnimation { duration: 150 } }
                HoverHandler { cursorShape: Qt.IBeamCursor; enabled: !field.activeFocus }
            }

            TextField {
                id: field
                anchors.left: parent.left
                anchors.right: revealBtn.visible ? revealBtn.left : (unitText.visible ? unitText.left : parent.right)
                anchors.verticalCenter: root.multiline ? undefined : parent.verticalCenter
                anchors.top: root.multiline ? parent.top : undefined
                anchors.bottom: root.multiline ? parent.bottom : undefined
                anchors.leftMargin: 12 * scaleFactor
                anchors.rightMargin: 12 * scaleFactor
                anchors.topMargin: root.multiline ? 6 * scaleFactor : 0
                anchors.bottomMargin: root.multiline ? 6 * scaleFactor : 0
                verticalAlignment: root.multiline ? TextInput.AlignTop : TextInput.AlignVCenter
                wrapMode: root.multiline ? Text.Wrap : Text.NoWrap
                color: "#46536D"
                font.pixelSize: 13 * scaleFactor
                font.family: "Microsoft YaHei UI"
                text: root.text
                placeholderText: root.placeholder
                placeholderTextColor: "#8A92A8"
                echoMode: root.password && !root._revealed ? TextInput.Password : TextInput.Normal
                selectByMouse: true
                background: Item {}
                onTextEdited: {
                    root.text = field.text
                    root.textEdited(root.text)
                }
            }

            // Lightweight trailing unit label (e.g. "cm"), never a pill button.
            Text {
                id: unitText
                visible: root.unit !== ""
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                anchors.rightMargin: 12 * scaleFactor
                text: root.unit
                color: "#8A92A8"
                font.pixelSize: 11 * scaleFactor
                font.family: "Microsoft YaHei UI"
            }

            Item {
                id: revealBtn
                property bool _on: false
                visible: root.revealable
                anchors.right: parent.right
                anchors.verticalCenter: parent.verticalCenter
                width: visible ? 30 * scaleFactor : 0
                height: 30 * scaleFactor

                Rectangle {
                    anchors.centerIn: parent
                    width: 26 * scaleFactor
                    height: 26 * scaleFactor
                    radius: width / 2
                    color: revealHover.hovered ? Qt.rgba(1.0, 1.0, 1.0, 0.30) : "transparent"
                    Behavior on color { ColorAnimation { duration: 120 } }
                }

                // Vector eye icon (no image asset, no new file). The slash
                // denotes eye-off (revealed). It only ever reflects the user's
                // current input via echoMode; it never reads a stored key.
                Canvas {
                    id: eyeIcon
                    anchors.centerIn: parent
                    width: 18 * scaleFactor
                    height: 18 * scaleFactor
                    property bool revealed: revealBtn._on
                    property bool hovered: revealHover.hovered
                    onRevealedChanged: requestPaint()
                    onHoveredChanged: requestPaint()
                    onPaint: {
                        var ctx = getContext("2d")
                        ctx.reset()
                        var c = eyeIcon.hovered ? "#4C5670" : "#7A7F9C"
                        ctx.strokeStyle = c
                        ctx.fillStyle = c
                        ctx.lineWidth = 1.4
                        ctx.beginPath()
                        ctx.moveTo(1, 9)
                        ctx.quadraticCurveTo(9, 1.5, 17, 9)
                        ctx.quadraticCurveTo(9, 16.5, 1, 9)
                        ctx.stroke()
                        ctx.beginPath()
                        ctx.arc(9, 9, 2.6, 0, Math.PI * 2)
                        ctx.fill()
                        if (eyeIcon.revealed) {
                            ctx.beginPath()
                            ctx.moveTo(2.5, 2.5)
                            ctx.lineTo(15.5, 15.5)
                            ctx.stroke()
                        }
                    }
                }

                HoverHandler { id: revealHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: revealBtn._on = !revealBtn._on }
            }
        }
    }
}
