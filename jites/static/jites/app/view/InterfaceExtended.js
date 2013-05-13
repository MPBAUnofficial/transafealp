/**
 * Created with PyCharm.
 * User: droghetti
 * Date: 5/8/13
 * Time: 5:58 PM
 * To change this template use File | Settings | File Templates.
 */
Ext.define('Jites.view.InterfaceExtended',{
    extend: 'Ext.panel.Panel',

    alias : 'widget.interface',

    layout: {
        type: 'table',
        columns: 2
    },

    initComponent: function() {
        var me = this

        me.items = [
            {
                xtype: 'panel',
                id: 'actiongraph',
                width: me.componentSize.wRow1,
                height: me.componentSize.hRow1
            },{
                xtype: 'panel',
                id: 'actiondetails',
                width: me.componentSize.wRow1,
                height: me.componentSize.hRow1
            },{
                xtype: 'panel',
                id: 'webgis',
                width: me.componentSize.wRow1,
                height: me.componentSize.hRow2
            },{
                xtype: 'panel',
                id: 'chronology',
                width: me.componentSize.wRow1,
                height: me.componentSize.hRow2
            }
        ];

        this.callParent(arguments);
    }
});