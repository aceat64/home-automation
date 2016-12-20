var getUrlParameter = function getUrlParameter(sParam) {
  var sPageURL = decodeURIComponent(window.location.search.substring(1)),
    sURLVariables = sPageURL.split('&'),
    sParameterName,
    i;

  for (i = 0; i < sURLVariables.length; i++) {
    sParameterName = sURLVariables[i].split('=');

    if (sParameterName[0] === sParam) {
      return sParameterName[1] === undefined ? true : sParameterName[1];
    }
  }
};

var apikey = getUrlParameter('key');

// Load Skycons for weather icons
var skycons = new Skycons({color:"#cfd2da"});

// Placeholder stuff
var eth0_data = {
  in: [],
  out: []
};
var power_data = [];

// How many data points to keep for graphs
var totalPoints = 100;

// Options for network graph
var network_options = {
  legend: {
    backgroundColor: 'transparent',
    color: '#cfd2da'
  },
  grid: {
    color: '#cfd2da',
  },
	series: {
    shadowSize:0,
    lines: {
      show: true
    }
  },
  yaxis: {
    min: 0,
    max: 150,
    color: '#cfd2da',
    show: true
  },
  xaxis: {
    show: false
  }
};

// Options for power graph
var power_options = {
  legend: {
    show: false
  },
  grid: {
    color: '#cfd2da',
  },
	series: {
    shadowSize:0,
    lines: {
      show: true
    }
  },
  yaxis: {
    min: 0,
    color: '#cfd2da',
    show: true,
    tickFormatter: function(v, axis) {
      if (v >= 1000) {
        return v.toFixed(axis.tickDecimals)/1000 + " kW";
      } else {
        return v.toFixed(axis.tickDecimals) + " W";
      }
    }
  },
  xaxis: {
    show: false
  }
};

// Grab initial state data so things aren't just blank/broken
$.get('https://your.hass.install/api/states?api_password=' + apikey, function(data) {
  last_response = new Date();
  data.forEach(function (item) {
    switch (item.entity_id) {
      case 'sensor.dark_sky_icon':
        console.log("INIT: sensor.dark_sky_icon: " + item.state);
        switch (item.state) {
          case 'clear-day':
            skycons.add("weather-icon", Skycons.CLEAR_DAY);
            break;
          case 'clear-night':
            skycons.add("weather-icon", Skycons.CLEAR_NIGHT);
            break;
          case 'rain':
            skycons.add("weather-icon", Skycons.RAIN);
            break;
          case 'snow':
            skycons.add("weather-icon", Skycons.SNOW);
            break;
          case 'sleet':
            skycons.add("weather-icon", Skycons.SLEET);
            break;
          case 'wind':
            skycons.add("weather-icon", Skycons.WIND);
            break;
          case 'fog':
            skycons.add("weather-icon", Skycons.FOG);
            break;
          case 'cloudy':
            skycons.add("weather-icon", Skycons.CLOUDY);
            break;
          case 'partly-cloudy-day':
            skycons.add("weather-icon", Skycons.PARTLY_CLOUDY_DAY);
            break;
          case 'partly-cloudy-night':
            skycons.add("weather-icon", Skycons.PARTLY_CLOUDY_NIGHT);
            break;
        }

        skycons.play();
        break;
      case 'sensor.dark_sky_temperature':
        console.log("INIT: sensor.dark_sky_temperature: " + item.state);
        $('#weather_temperature').text(Math.round(item.state));
        break;
      case 'sensor.dark_sky_summary':
        console.log("INIT: sensor.dark_sky_summary: " + item.state);
        $('#weather_summary').text(item.state);
        break;
      case 'sensor.dark_sky_apparent_temperature':
        console.log("INIT: sensor.dark_sky_apparent_temperature: " + item.state);
        $('#weather_apparent_temperature').text(Math.round(item.state));
        break;
      case 'sensor.dark_sky_minutely_summary':
        console.log("INIT: sensor.dark_sky_minutely_summary: " + item.state);
        $('#weather_minutely_summary').text(item.state);
        break;
      case 'sensor.dark_sky_hourly_summary':
        console.log("INIT: sensor.dark_sky_hourly_summary: " + item.state);
        $('#weather_hourly_summary').text(item.state);
        break;
      case 'sensor.dark_sky_daily_summary':
        console.log("INIT: sensor.dark_sky_daily_summary: " + item.state);
        $('#weather_daily_summary').text(item.state);
        break;
      case 'sensor.aeotec_dsb09104_home_energy_meter_power_3_4':
        console.log("INIT: sensor.aeotec_dsb09104_home_energy_meter_power_3_4: " + item.state);
        power = item.state;
        break;
      case 'sensor.eth0_in':
        console.log("INIT: sensor.eth0_in: " + item.state);
        eth0_in = item.state / 1000000;
        break;
      case 'sensor.eth0_out':
        console.log("INIT: sensor.eth0_out: " + item.state);
        eth0_out = item.state / 1000000;
        break;
      case 'sensor.coinbase_price':
        console.log("INIT: sensor.coinbase_price: " + item.state);
        $('#coinbase_price').text(item.state);
        break;
      case 'climate.hallway':
        nest = item.attributes;
        console.log("INIT: climate.hallway: " + JSON.stringify(nest));
        updateNest();
        break;
      case 'switch.garage_door':
        console.log("INIT: switch.garage_door: " + item.state);
        $('#garage_door').text(item.state);
        if (item.state == "open") {
          $("#garage_door").addClass("text-warning");
        } else {
          $("#garage_door").removeClass("text-warning");
        }
        break;
      case 'device_tracker.android1234':
        console.log("INIT: device_tracker.android1234: " + item.state);
        $('#nexus_5x').text(item.state.split('_').join(' '));
        break;
      case 'device_tracker.android5678':
        console.log("INIT: device_tracker.android5678: " + item.state);
        $('#pixel_xl').text(item.state.split('_').join(' '));
        break;
    }
  });

  /**
   * Update network and power graphs
   */
  updateNetworkGraph();
  updatePowerGraph();

  // connect to stream
  var source = new EventSource('https://your.hass.install/api/stream?api_password=' + apikey);

  source.addEventListener('open', function(e) {
    console.log('Connection established');
  }, false);

  source.addEventListener('error', function(event) {
    console.log('Error!');
    if (event.target.readyState == EventSource.CLOSED) {
      $(".alert").text("Connection to server lost!").slideDown(200);
      console.log('Connection was closed!');

      setInterval(function () {
        // try connecting, if it works, refresh
        $.get('https://your.hass.install/api/?api_password=' + apikey, null, function() {
          location.reload();
        });
      }, 5000);
    }
  }, false);

  // do things when events are received
  source.addEventListener('message', function(event) {
    if ("ping" === event.data) {
      return;
    }

    var item = JSON.parse(event.data).data;

    if (typeof item.new_state !== "undefined") {
      switch (item.entity_id) {
        case 'sensor.dark_sky_icon':
          //console.log("sensor.dark_sky_icon: " + item.new_state.state);
          switch (item.new_state.state) {
            case 'clear-day':
              skycons.set("weather-icon", Skycons.CLEAR_DAY);
              break;
            case 'clear-night':
              skycons.set("weather-icon", Skycons.CLEAR_NIGHT);
              break;
            case 'rain':
              skycons.set("weather-icon", Skycons.RAIN);
              break;
            case 'snow':
              skycons.set("weather-icon", Skycons.SNOW);
              break;
            case 'sleet':
              skycons.set("weather-icon", Skycons.SLEET);
              break;
            case 'wind':
              skycons.set("weather-icon", Skycons.WIND);
              break;
            case 'fog':
              skycons.set("weather-icon", Skycons.FOG);
              break;
            case 'cloudy':
              skycons.set("weather-icon", Skycons.CLOUDY);
              break;
            case 'partly-cloudy-day':
              skycons.set("weather-icon", Skycons.PARTLY_CLOUDY_DAY);
              break;
            case 'partly-cloudy-night':
              skycons.set("weather-icon", Skycons.PARTLY_CLOUDY_NIGHT);
              break;
          }
          break;
        case 'sensor.dark_sky_temperature':
          //console.log("sensor.dark_sky_temperature: " + item.new_state.state);
          $('#weather_temperature').text(Math.round(item.new_state.state));
          break;
        case 'sensor.dark_sky_summary':
          //console.log("sensor.dark_sky_summary: " + item.new_state.state);
          $('#weather_summary').text(item.new_state.state);
          break;
        case 'sensor.dark_sky_apparent_temperature':
          //console.log("sensor.dark_sky_apparent_temperature: " + item.new_state.state);
          $('#weather_apparent_temperature').text(Math.round(item.new_state.state));
          break;
        case 'sensor.dark_sky_minutely_summary':
          //console.log("sensor.dark_sky_minutely_summary: " + item.new_state.state);
          $('#weather_minutely_summary').text(item.new_state.state);
          break;
        case 'sensor.dark_sky_hourly_summary':
          //console.log("sensor.dark_sky_hourly_summary: " + item.new_state.state);
          $('#weather_hourly_summary').text(item.new_state.state);
          break;
        case 'sensor.dark_sky_daily_summary':
          //console.log("sensor.dark_sky_daily_summary: " + item.new_state.state);
          $('#weather_daily_summary').text(item.new_state.state);
          break;
        case 'sensor.aeotec_dsb09104_home_energy_meter_power_3_4':
          power = item.new_state.state;
          //console.log("sensor.aeotec_dsb09104_home_energy_meter_power_3_4: " + power + " W");
          updatePowerGraph();
          break;
        case 'sensor.coinbase_price':
          //console.log("sensor.coinbase_price: " + item.new_state.state);
          $('#coinbase_price').text(item.new_state.state);
          break;
        case 'climate.hallway':
          nest = item.new_state.attributes;
          //console.log("climate.hallway: " + JSON.stringify(nest));
          updateNest();
          break;
        case 'switch.garage_door':
          //console.log("switch.garage_door: " + item.new_state.state);
          $('#garage_door').text(item.new_state.state);
          if (item.state == "open") {
            $("#garage_door").addClass("text-warning");
          } else {
            $("#garage_door").removeClass("text-warning");
          }
          break;
        case 'device_tracker.android1234':
          //console.log("device_tracker.android1234: " + item.state);
          $('#nexus_5x').text(item.state.split('_').join(' '));
          break;
        case 'device_tracker.android5678':
          //console.log("device_tracker.android5678: " + item.state);
          $('#pixel_xl').text(item.state.split('_').join(' '));
          break;
      }
    } else if (item.topic == "home/router/eth0") {
      // We're using the MQTT message since it has both in and out info at the same time
      var readings = JSON.parse(item.payload);
      eth0_in = readings.in / 1000000;
      eth0_out  = readings.out / 1000000;
      //console.log("sensor.eth0_in: " + eth0_in + " Mbps");
      //console.log("sensor.eth0_out: " + eth0_out + " Mbps");

      updateNetworkGraph();
    }
  }, false);
});

/**
 * Update the network graph
 */
function updateNetworkGraph() {
  var text_in;
  var text_out;
  var nice_in = eth0_in.toFixed(2);
  var nice_out = eth0_out.toFixed(2);
  $('#eth0_in').text(nice_in);
  $('#eth0_out').text(nice_out);

  if (eth0_data.in.length > 0)
    eth0_data.in = eth0_data.in.slice(1);
  if (eth0_data.out.length > 0)
    eth0_data.out = eth0_data.out.slice(1);

  while (eth0_data.in.length < totalPoints) {
    var x = eth0_in;
    if (x < 0)
      x = 0;
    if (isNaN(x))
      x = 0;
    eth0_data.in.push(x);
  }

  while (eth0_data.out.length < totalPoints) {
    var y = eth0_out;
    if (y < 0)
      y = 0;
    if (isNaN(y))
      y = 0;
    eth0_data.out.push(y);
  }

  // zip the generated y values with the x values
  var res_in = [];
  var res_out = [];
  for (var i = 0; i < eth0_data.in.length; ++i){
    res_in.push([i, eth0_data.in[i]]);
  }
  for (i = 0; i < eth0_data.out.length; ++i){
    res_out.push([i, eth0_data.out[i]]);
  }

  var series = [
    {
      label: "In",
      data: res_in
    },
    {
      label: "Out",
      data: res_out
    }
  ];

  $.plot($("#eth0-graph"), series, network_options);
}

/**
 * Update the power graph
 */
function updatePowerGraph() {
  var text;
  var nice = Math.round(power);
  if (nice <= 400) {
    $('#power').removeClass("text-warning");
    $('#power').removeClass("text-danger");

    $('#power').addClass("text-success");
  } else if (nice >= 5000 && nice <= 10000) {
    $('#power').removeClass("text-success");
    $('#power').removeClass("text-danger");

    $('#power').addClass("text-warning");
  } else if (nice > 10000) {
    $('#power').removeClass("text-success");
    $('#power').removeClass("text-warning");

    $('#power').addClass("text-danger");
  } else {
    $('#power').removeClass("text-success");
    $('#power').removeClass("text-warning");
    $('#power').removeClass("text-danger");
  }

  if (nice >= 1000) {
    nice = nice / 1000;
    text = nice.toFixed(2) + " kW";
  } else {
    text = nice + " W";
  }
  $('#power').text(text);

  if (power_data.length > 0)
    power_data = power_data.slice(1);

  while (power_data.length < totalPoints) {
    var y = Math.round(power);
    if (y < 0)
      y = 0;
    if (isNaN(y))
      y = 0;
    power_data.push(y);
  }

  // zip the generated y values with the x values
  var res = [];
  for (var i = 0; i < power_data.length; ++i){
    res.push([i, power_data[i]]);
  }

  var series = [
    {
      label: "Power",
      data: res,
      constraints: [
        {
          threshold: 400,
          color: "#5cb85c",
          evaluate : function(y, threshold) { return y <= threshold; }
        },
        {
          threshold: 5000,
          color: "#f0ad4e",
          evaluate : function(y, threshold) { return y >= threshold && y <= 10000; }
        },
        {
          threshold: 10000,
          color: "#d9534f",
          evaluate : function(y, threshold) { return y > threshold; }
        }
      ]
    }
  ];

  $.plot($("#power-graph"), series, power_options);
}

/**
 * Update nest card
 */
function updateNest() {
  if (nest.away_mode == "on") {
    $("#nest_operation").text("Away");
    $("#nest_target_temp").text(nest.target_temp_low + " · " + nest.target_temp_high);
  } else {
    if (nest.operation_mode == "cool") {
      $("#nest_operation").text("Cooling To");
      $("#nest_target_temp").text(nest.temperature);
    } else if (nest.operation_mode == "heat") {
      $("#nest_operation").text("Heating To");
      $("#nest_target_temp").text(nest.temperature);
    } else {
      $("#nest_target_temp").text(nest.target_temp_low + " · " + nest.target_temp_high);
    }
  }

  $("#nest_current_temp").text(nest.current_temperature);
}

/**
 * Google Maps + Traffic
 * https://snazzymaps.com/style/2/midnight-commander
 */
var style = [{"featureType":"all","elementType":"labels.text","stylers":[{"visibility":"off"}]},{"featureType":"all","elementType":"labels.icon","stylers":[{"visibility":"off"}]},{"featureType":"administrative","elementType":"geometry.fill","stylers":[{"color":"#000000"}]},{"featureType":"administrative","elementType":"geometry.stroke","stylers":[{"color":"#144b53"},{"lightness":14},{"weight":1.4}]},{"featureType":"landscape","elementType":"all","stylers":[{"color":"#08304b"}]},{"featureType":"poi","elementType":"geometry","stylers":[{"color":"#0c4152"},{"lightness":5}]},{"featureType":"road.highway","elementType":"geometry.fill","stylers":[{"color":"#000000"}]},{"featureType":"road.highway","elementType":"geometry.stroke","stylers":[{"color":"#0b434f"},{"lightness":25}]},{"featureType":"road.arterial","elementType":"geometry.fill","stylers":[{"color":"#000000"}]},{"featureType":"road.arterial","elementType":"geometry.stroke","stylers":[{"color":"#0b3d51"},{"lightness":16}]},{"featureType":"road.local","elementType":"geometry","stylers":[{"color":"#000000"}]},{"featureType":"transit","elementType":"all","stylers":[{"color":"#146474"}]},{"featureType":"water","elementType":"all","stylers":[{"color":"#021019"}]}];

function initMap() {
  map = new google.maps.Map(document.getElementById('map'), {
    zoom: 10,
    center: {lat: 32.98, lng: -96.87},
    disableDefaultUI: true,
    clickableIcons: false,
    disableDoubleClickZoom: true,
    draggable: false,
    scrollwheel: false,
    zoomControl: false
  });
  map.setOptions({styles: style});

  var trafficLayer = new google.maps.TrafficLayer();
  trafficLayer.setMap(map);
  setInterval(reloadTiles, 300000);
}

/**
 * Hack to auto-update google maps, this will eventually break!
 * See: http://stackoverflow.com/a/27904920
 */
function reloadTiles() {
  console.log('updating map');
  var tiles = $("#map").find("img");
  for (var i = 0; i < tiles.length; i++) {
    var src = $(tiles[i]).attr("src");
    if (/googleapis.com\/maps\/vt\?pb=/.test(src)) {
      var new_src = src.split("&ts")[0] + '&ts=' + (new Date()).getTime();
      $(tiles[i]).attr("src", new_src);
    }
  }
}

/**
 * Weather modal
 */
$('#wunderground-modal').on('show.bs.modal	', function () {
  // Open the page
  $('#wunderground').attr("src","https://www.wunderground.com/us/tx/carrollton/zmw:75007.1.99999");
  // After 1.5 seconds, take us to the forecast
  setTimeout(function () {
    $('#wunderground').attr("src","https://www.wunderground.com/us/tx/carrollton/zmw:75007.1.99999#forecast");
  }, 2000);
});
$('#wunderground-modal').on('hide.bs.modal', function () {
  $('#wunderground').attr("src","");
});
