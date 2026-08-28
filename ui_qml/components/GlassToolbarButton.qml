import QtQuick

Item {
    id: root
    signal clicked()

    property url iconSource: ""
    property string label: ""
    property real scaleFactor: 1.0

    implicitWidth: 92 * scaleFactor
    implicitHeight: 46 * scaleFactor
    width: implicitWidth
    height: implicitHeight
    readonly property real radius: 22 * scaleFactor

    readonly property bool _hovered: hover.hovered
    readonly property bool _pressed: tap.pressed

    HoverHandler { id: hover; cursorShape: Qt.PointingHandCursor }
    TapHandler { id: tap; onTapped: root.clicked() }

    // The frosted blur comes from HomePage's single shared blur layer (masked
    // to this button's footprint). Here: only the translucent glass tint, the
    // thin border and the content. No shadow, no halo, no enlarged layer.
    Item {
        id: body
        anchors.fill: parent
        scale: root._pressed ? 0.985 : (root._hovered ? 1.01 : 1.0)
        y: root._hovered ? (root._pressed ? 0 : -1 * scaleFactor) : 0
        transformOrigin: Item.Center
        Behavior on scale { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }
        Behavior on y { NumberAnimation { duration: 120; easing.type: Easing.OutCubic } }

        Rectangle {
            id: glass
            anchors.fill: parent
            radius: root.radius
            color: Qt.rgba(1.0, 1.0, 1.0, root._hovered ? 0.42 : 0.26)
            border.width: 1
            border.color: Qt.rgba(1.0, 1.0, 1.0, root._hovered ? 0.60 : 0.34)
            Behavior on color { ColorAnimation { duration: 150 } }
            Behavior on border.color { ColorAnimation { duration: 150 } }
        }

        Row {
            anchors.centerIn: parent
            spacing: 6 * scaleFactor
            Item {
                width: 26 * scaleFactor
                height: 26 * scaleFactor
                anchors.verticalCenter: parent.verticalCenter
                Rectangle {
                    anchors.fill: parent
                    radius: width / 2
                    color: Qt.rgba(0.97, 0.93, 0.94, 0.28)
                }
                Image {
                    anchors.centerIn: parent
                    source: root.iconSource
                    width: 22 * scaleFactor
                    height: 22 * scaleFactor
                    fillMode: Image.PreserveAspectFit
                    sourceSize: Qt.size(22 * scaleFactor, 22 * scaleFactor)
                    opacity: 0.92
                    scale: root._hovered ? 1.06 : 1.0
                    transformOrigin: Item.Center
                    Behavior on scale { NumberAnimation { duration: 150 } }
                }
            }
            Text {
                text: root.label
                color: "#536B89"
                font.pixelSize: 12 * scaleFactor
                font.weight: Font.DemiBold
                font.family: "Microsoft YaHei UI"
                anchors.verticalCenter: parent.verticalCenter
            }
        }
    }
}
