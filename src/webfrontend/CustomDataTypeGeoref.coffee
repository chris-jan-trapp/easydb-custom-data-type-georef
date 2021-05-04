class CustomDataTypeGeoref extends CustomDataTypeWithCommons

  #######################################################################
  # return name of plugin
  getCustomDataTypeName: ->
    "custom:base.custom-data-type-georef.georef"

  #######################################################################
  # return name (l10n) of plugin
  getCustomDataTypeNameLocalized: ->
    $$("custom.data.type.georef.name")

  #######################################################################
  # show popover and fill it with the form-elements
  showEditPopover: (btn, data, cdata, layout, opts) ->
    cdata_form = new CUI.Form
      data: cdata
      fields: @__getEditorFields(cdata)
      onDataChanged: =>
        @__updateResult(cdata, layout, opts)
        @__setEditorFieldStatus(cdata, layout)
    .start()

    xmapboxpane = new CUI.SimplePane
        class: "georef_mapbox_container"
        header_left:
            new CUI.Label
                text: "Satellit und Straßen"
        content:
            new CUI.Label
                text: ""

    @popover = new CUI.Popover
      element: btn
      fill_space: "both"
      placement: "c"
      pane:
        # titel of popovers
        header_left: new CUI.Label(text: $$('custom.data.type.georef.name'))
        # "save"-button
        footer_right: []
        footer_left: cdata_form

        # "reset"-button
        content: xmapboxpane
    .show()
    @__initMap(cdata, cdata_form, layout, opts)


  ##########################################################################
  # initialisiere Karte
  __initMap: (cdata, cdata_form, layout, opts) ->
    console.log "Map initialized"
    that = @

    mapbox_access_token = ''
    if @getCustomSchemaSettings().mapbox_access_token?.value
      mapbox_access_token = @getCustomSchemaSettings().mapbox_access_token?.value
    else
      console.log "Kein Mapbox-Api-Key gegeben!"

    mapboxgl.accessToken = mapbox_access_token
    container = document.getElementsByClassName('georef_mapbox_container')[0]

    # remove all style + classes + content from container
    container.removeAttribute('class')
    container.removeAttribute('style')
    container.removeAttribute('id')
    container.className = 'georef_mapbox_container'
    container.innerHTML = ''

    map = new mapboxgl.Map({
        container: container
        style: 'mapbox://styles/mapbox/satellite-streets-v10'
        center: [9.935,51.5338]
        zoom: 5
    });

    # disable map rotation using right click + drag
    map.dragRotate.disable()

    # disable map rotation using touch rotation gesture
    map.touchZoomRotate.disableRotation()

    #nav = new mapboxgl.NavigationControl()
    #map.addControl(nav, 'top-left')

    draw = new MapboxDraw(
      displayControlsDefault: false
      controls:
        polygon: true
        point: true
        line_string: true
        trash: false)

    map.addControl(draw)

    map.dragPan.enable()
    full_uri = 'https://odysseus.gbv.de:8443/geoserver/ogc/features/collections/gbv:teller/items?limit=1000000&filter=NOT%20IN%20%28%27teller.1231%27%29&filter-lang=cql-text&additionalProp1='
    data = draw.getAll()
    feature_source = 'https://odysseus.gbv.de:8443/geoserver/ogc/features/collections/gbv:teller/items?f=application%2Fjson'
    others_filter = ""
    subject_filter = ""
    if cdata.feature_id
      others_filter = "NOT IN ('" + cdata.feature_id + "')"
      others_filter = "&filter=" + encodeURIComponent others_filter
      others_filter = others_filter + "&filter-lang=cql-text"

      subject_filter = "IN ('" + cdata.feature_id + "')"
      subject_filter = "&filter=" + encodeURIComponent others_filter
      subject_filter = others_filter + "&filter-lang=cql-text"


    map.on 'load', ->
      others_source = feature_source + others_filter
      map.addSource 'teller',
        'type': 'geojson',
        'data': others_source

      console.log 'Source added from : ' + others_source
      map.addLayer
          'id': 'teller',
          'type': 'symbol',
          'source': 'teller'
          'layout':
            'icon-image': 'circle-15'
          'paint':
            'icon-color': '#fc7133'

      if subject_filter
        map.addSource 'subject',
          'type': 'geojson',
          'data': feature_source + subject_filter
        map.addLayer
          'id': 'subject',
          'type': 'symbol',
          'source': 'teller'
          'layout':
            'icon-image': 'circle-15'
          'paint':
            'icon-color': '#3afcc8'

    map.on 'draw.update', ->
      console.log 'redraw'
      map.getSource('teller').setData(feature_source + others_filter)


    # click on map
    map.on 'click', (e) ->
      data = draw.getAll()
      if data.features.length == 1
        geoJSON = data.features[0]
        delete geoJSON.id
        type = data.features[0].geometry.type
        if type == 'Point'
          if data.features[0].geometry.coordinates.length == 2
            geoJSON = JSON.stringify(geoJSON)
            coords = data.features[0].geometry.coordinates
            coords = coords.join(' ')
            # lock in save data
            cdata.conceptURI = geoJSON
            cdata.conceptName = 'Point'
            that.__updateResult(cdata, layout, opts)
        if type == 'LineString'
          if data.features[0].geometry.coordinates.length >= 2
            geoJSON = JSON.stringify(geoJSON)
            line = data.features[0].geometry.coordinates
            linePoints = new Array
            for value in line
              linePoints.push value.join(' ')
            linePoints = linePoints.join(',')
            # lock in save data
            cdata.conceptURI = geoJSON
            cdata.conceptName = 'LineString'
            that.__updateResult(cdata, layout, opts)

        if type == 'Polygon'
          # Each LinearRing of a Polygon must have 4 or more Positions
          if data.features[0].geometry.coordinates[0].length >= 5
            polygonCoords = data.features[0].geometry.coordinates

            # rewind the polygon to right hand rule (geojson-spec 1.0)
            turfPolygon = turf.polygon.polygon(polygonCoords)
            rewind = turf.rewind(turfPolygon);
            geoJSON.geometry.coordinates = rewind.geometry.coordinates
            geoJSON = JSON.stringify(geoJSON)

            # lock in save data
            cdata.conceptURI = geoJSON
            cdata.conceptName = 'Polygon'
            that.__updateResult(cdata, layout, opts)
      return

    # add click listener on type-buttons
    typebuttons = document.getElementsByClassName('mapbox-gl-draw_ctrl-draw-btn')

    # click on "type" button (polygon, line, point)
    checkFormCount = ->

      # reset form
      cdata.conceptURI = ''
      cdata.conceptName = ''

      # check if only one form, else delete others
      data = draw.getAll();
      if data.features
        if data.features.length > 1
          if data.features[0].geometry.coordinates.length > 0
            # disable "save"button

            # delete all current features
            draw.deleteAll()
            # trigger click on button to return to ready-status    ###
            xselectorArr = document.querySelector('.mapbox-gl-draw_ctrl-draw-btn.active').className.split(' ')
            xselector = '.' + xselectorArr[0] + '.' + xselectorArr[1]
            document.querySelector(xselector).click();
            document.querySelector(xselector).click();
      return

    i = 0
    while i < typebuttons.length
      typebuttons[i].addEventListener 'click', checkFormCount, false
      i++



  #########################################################################
  # create form
  __getEditorFields: (cdata) ->
    fields = []

    fields


  #######################################################################
  # checks the form and returns status
  getDataStatus: (cdata) ->
    if (cdata)
        if cdata.conceptURI and cdata.conceptName

          # check geojson
          geoJSONCheck = 0
          try
            json = JSON.parse(cdata.conceptURI)
          catch exception
            json = null
          if json
            geoJSONCheck = 1

          # check type
          typeCheck = if cdata.conceptName then cdata.conceptName.trim() else undefined

          if geoJSONCheck and typeCheck
            return "ok"

          if cdata.conceptURI.trim() == '' and cdata.conceptName.trim() == ''
            return "empty"

          return "invalid"
        else
          cdata = {
                conceptName : ''
                conceptURI : ''
            }
          return "empty"
    else
      cdata = {
            conceptName : ''
            conceptURI : ''
        }
      return "empty"


  #######################################################################
  # generates static mapbox-map via geojson
  __getStaticMapboxMap: (cdata) ->
    that = @
    mapContent = new CUI.Label
                  text: $$('custom.data.type.georef.edit.kartenansicht')
    htmlContent = 'no map available'
    # read mapbox_access_token from schema
    if that.getCustomSchemaSettings().mapbox_access_token?.value
        mapbox_access_token = that.getCustomSchemaSettings().mapbox_access_token?.value
    if mapbox_access_token
        # compare to https://www.mapbox.com/mapbox.js/example/v1.0.0/static-map-from-geojson-with-geo-viewport/
        jsonStr = '{"type": "FeatureCollection","features": []}'
        json = JSON.parse(jsonStr)
        json.features.push JSON.parse(cdata.conceptURI)
        bounds = geojsonExtent(json)
        if bounds
          size = [
            500
            300
          ]
          vp = geoViewport.viewport(bounds, size)
          encodedGeoJSON = JSON.parse(cdata.conceptURI)
          encodedGeoJSON.properties['stroke-width'] = 4
          encodedGeoJSON.properties['stroke'] = '#C20000'
          encodedGeoJSON = JSON.stringify(encodedGeoJSON)
          encodedGeoJSON = encodeURIComponent(encodedGeoJSON)
          centerCoords = vp.center
          if centerCoords[0] > 180
            centerCoords[0] = centerCoords[0] - 360
          if centerCoords[0] < -180
            centerCoords[0] = centerCoords[0] + 360
          centerCoords = centerCoords.join ','
          zoomFaktor = vp.zoom
          if zoomFaktor >= 2
            zoomFaktor = zoomFaktor - 2
          else if zoomFaktor == 1
            zoomFaktor = 0
          imageSrc = location.protocol + '//api.mapbox.com/styles/v1/mapbox/satellite-streets-v9/static/geojson(' + encodedGeoJSON + ')/' +  centerCoords + ',' + zoomFaktor + '/500x300@2x?access_token=' + mapbox_access_token
          htmlContent = "<div style=\"width:500px; height: 300px; background-color: gray; background-image: url('" + imageSrc  + "'); background-repeat: no-repeat; background-position: center center; background-size: contain;\"></div>"
      else
        htmlContent = "no mapbox-access-token for georef"
    mapContent.DOM.innerHTML = htmlContent
    mapContent

  #######################################################################
  # generates static mapbox-map via geojson

  __getUsuableMapboxMap: (cdata) ->
    that = @
    mapContent = new CUI.Label
                  text: $$('custom.data.type.georef.edit.kartenansicht')
    "__getUsuableMapboxMap"


  #######################################################################
  # update result in Masterform
  __updateResult: (cdata, layout, opts) ->
    that = @
    # if field is not empty
    if cdata?.conceptURI
      # die uuid einkürzen..
      displayURI = cdata.conceptURI
      displayURI = displayURI.replace('http://', '')
      displayURI = displayURI.replace('https://', '')
      uriParts = displayURI.split('/')
      uuid = uriParts.pop()
      if uuid.length > 10
        uuid = uuid.substring(0,5) + '…'
        uriParts.push(uuid)
        displayURI = uriParts.join('/')

      mapContent = @__getStaticMapboxMap(cdata)

      copyrightLabel = new CUI.Label
                      text: "Copyright"
                      size: "mini"
      copyrightLabel.DOM.innerHTML = "©&nbsp;<a href='https://www.mapbox.com/about/maps/'>Mapbox</a>&nbsp;&nbsp;©&nbsp;<a href='http://www.openstreetmap.org/copyright'>OpenStreetMap</a>&nbsp;&nbsp;<strong><a href='https://www.mapbox.com/map-feedback/' target='_blank'>Improve this map</a></strong>";


      info = new CUI.VerticalLayout
        class: 'ez5-info_commonPlugin'
        top:
          content:
            mapPane = new CUI.Pane
              class: "cui-mapbox-georef-pane"
              top:
                content: [
                  new CUI.PaneHeader
                    left:
                      content:
                        new CUI.Label
                          text: cdata.conceptName + ' (' + $$('custom.data.type.georef.edit.kartenansicht') + ')'
                    right:
                      content: [
                        #CUI.Pane.getToggleFillScreenButton()
                      ]
                ]
              center:
                content: mapContent

      layout.replace(info, 'center')
      layout.addClass('ez5-linked-object-edit')
      options =
        class: 'ez5-linked-object-container'
      layout.__initPane(options, 'center')

    # if field is empty, display searchfield
    if ! cdata?.conceptURI
      suggest_Menu_directInput

      inputX = new CUI.Input
                  class: "pluginDirectSelectEditInput"
                  undo_and_changed_support: false
                  name: "directSelectInput"
                  content_size: false
                  onKeyup: (input) =>
                    input.setValue('')
      inputX.render()

      # init suggestmenu
      suggest_Menu_directInput = new CUI.Menu
          element : inputX
          use_element_width_as_min_width: true

      # init xhr-object to abort running xhrs
      searchsuggest_xhr = { "xhr" : undefined }

      layout.replace(inputX, 'center')
      layout.removeClass('ez5-linked-object-edit')
      options =
        class: ''
      layout.__initPane(options, 'center')

    # did data change?
    that.__setEditorFieldStatus(cdata, layout)


  #######################################################################
  # renders the "result" in original form (outside popover)

  __renderButtonByData: (cdata) ->
    that = @
    # when status is empty or invalid --> message
    switch @getDataStatus(cdata)
      when "empty"
        return new CUI.EmptyLabel(text: $$("custom.data.type.georef.edit.no_georef")).DOM
      when "invalid"
        return new CUI.EmptyLabel(text: $$("custom.data.type.georef.edit.no_valid_georef")).DOM

    mapContent = @__getStaticMapboxMap(cdata)

    copyrightLabel = new CUI.Label
                    text: "Copyright"
                    size: "mini"
    copyrightLabel.DOM.innerHTML = "©&nbsp;<a href='https://www.mapbox.com/about/maps/'>Mapbox</a>&nbsp;&nbsp;©&nbsp;<a href='http://www.openstreetmap.org/copyright'>OpenStreetMap</a>&nbsp;&nbsp;<strong><a href='https://www.mapbox.com/map-feedback/' target='_blank'>Improve this map</a></strong>";

    mapPane = new CUI.Pane
      class: "cui-mapbox-georef-pane"
      top:
        content: [
          new CUI.PaneHeader
            left:
              content:
                new CUI.Label
                  text: cdata.conceptName + ' (' + $$('custom.data.type.georef.edit.kartenansicht') + ')'
            right:
              content: [
                #CUI.Pane.getToggleFillScreenButton()
              ]
        ]
      center:
        content: mapContent
      bottom:
        content: [
          new CUI.PaneFooter
            left:
              content: copyrightLabel
            right:
              content: ""
        ]

    CUI.Events.listen
       type: ["start-fill-screen", "end-fill-screen"]
       node: mapPane
       call: (ev) =>
          console.log "Event:", ev
          eventType = ev._type
          # if fullsize show usable map
          if (eventType == 'start-fill-screen')
            console.log "start-fill-screen"
            mapPane.replace(@__getUsuableMapboxMap(cdata), "center")
          # if normal view show small static map
          if (eventType == 'end-fill-screen')
            console.log "end-fill-screen"
            mapPane.replace(@__getStaticMapboxMap(cdata), "center")
          console.log "fertig eventiert"


    mapPane.DOM


  #######################################################################
  # zeige die gewählten Optionen im Datenmodell unter dem Button an
  getCustomDataOptionsInDatamodelInfo: (custom_settings) ->
    tags = []

    if custom_settings.mapbox_access_token?.value
      tags.push "✓ Mapbox-Access-Token"
    else
      tags.push "✘ Mapbox-Access-Token"

    tags

CustomDataType.register(CustomDataTypeGeoref)
