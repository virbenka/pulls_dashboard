$(document).ready(function() {
	$('.labels').select2();
});
$(document).ready(function() {
	$('.people').select2();
});
$(document).ready(function() {
	$('.tests_select').select2();
});
$(document).ready(function() {
	$('.people_type').select2(({
  placeholder: "Select a state"
});
$('.assignees_select').select2();
});
function filterTable() {
let dashboard = document.getElementById('Dashboard');
let rows = dashboard.rows;
var current_labels, author, current_people, found;
var rows_display = {};
let filters_num = 0;
for (var type in filters) {
  if (type == "mergeable") {
    if (filters[type] == true) {
      filters_num += 1;
      for (i = 1; i < rows.length; i++) {
	mergeable = rows[i].getElementsByClassName('mergeable')[0].id
	if (mergeable == "True") {
	  console.log("LALA");
	  if (rows_display[i]) {
	    rows_display[i] += 1;
	  } else {
	    rows_display[i] = 1;
	  }
	}
      }
    }
  } else if (type == "labels") {
    if (filters[type].length > 0) {
      filters_num += 1;
    } else {
      continue;
    }
    for (i = 1; i < rows.length; i++) {
      found = 0;
      current_labels = rows[i].getElementsByClassName('label');
      for (j = 0; j < current_labels.length; ++j) {
	if (filters[type].indexOf(current_labels[j].textContent) > -1) {
	  found += 1;
	}
      }
      if (found == filters[type].length) {
	if (rows_display[i]) {
	  rows_display[i] += 1;
	} else {
	  rows_display[i] = 1;
	}
      }
    }
  } else if (type == "tests_select") {
    if (filters[type].length > 0) {
      filters_num += 1;
    } else {
      continue;
    }
    for (i = 1; i < rows.length; i++) {
      found = 0;
      current_tests = rows[i].getElementsByClassName('successed_test');
      for (j = 0; j < current_tests.length; ++j) {
	if (filters[type].indexOf(current_tests[j].innerText) > -1) {
	  found += 1;
	}
      }
      if (found == filters[type].length) {
	if (rows_display[i]) {
	  rows_display[i] += 1;
	} else {
	  rows_display[i] = 1;
	}
      }
    }
  } else if (type == "assignees") {
    if (filters[type].length > 0) {
      filters_num += 1;
    } else {
      continue;
    }
    for (i = 1; i < rows.length; i++) {
      assignees = rows[i].getElementsByClassName('assignees_');
      console.log(assignees);
      for (j = 0; j < assignees.length; ++j) {
	if (filters[type].indexOf(assignees[j].id) > -1) {
	  console.log("found");
	  if (rows_display[i]) {
	    rows_display[i] += 1;
	  } else {
	    rows_display[i] = 1;
	  }
	  break;
	}
      }
    }
  } else if (type == "people") {
    if (filters[type].length > 0) {
      filters_num += 1;
    } else {
      continue;
    }
    for (i = 1; i < rows.length; i++) {
      author = rows[i].getElementsByClassName('author')[0].id;
      if (filters[type].indexOf(author) > -1) {
	if (rows_display[i]) {
	  rows_display[i] += 1;
	} else {
	  rows_display[i] = 1;
	}
      }
    }
  } else if (type == "people_type") {
      if (filters[type].length > 0) {
	filters_num += 1;
      } else {
	continue;
      }

      for (i = 1; i < rows.length; i++) {
	author_type = rows[i].getElementsByClassName('author_type')[0].id;
	if (author_type == "") {
	  author_type="other";
	}
	if (filters[type].indexOf((author_type+'s').toLowerCase()) > -1) {
	  if (rows_display[i]) {
	    rows_display[i] += 1;
	  } else {
	  rows_display[i] = 1;
	}
      }
    }
  }
}
if (filters_num > 0) {
  for (i = 1; i < rows.length; i++) {
    if (rows_display[i] == filters_num) {
      rows[i].style.display = "";
    } else {
      rows[i].style.display = "none";
    }
  }
} else {
  for (i = 1; i < rows.length; i++) {
    rows[i].style.display = "";
  }
}
}

var filters = {'mergeable': false};
var targetProxy = new Proxy(filters, {
	set: function (target, key, value) {
	  console.log(`${key} set to ${value}`);
	  filters[key] = value;
	  filterTable();
	  return true;
	}
});
$('.people').change(function () {
	var selectedItem = $('.people').val();
	targetProxy.people = selectedItem;
});
$('.labels').change(function () {
	var selectedItem = $('.labels').val();
	targetProxy.labels = selectedItem;
});
$('.tests_select').change(function () {
	var selectedItem = $('.tests_select').val();
	targetProxy.tests_select = selectedItem;
});
$('.people_type').change(function () {
	var selectedItem = $('.people_type').val();
	targetProxy.people_type = selectedItem;
});
$('.assignees_select').change(function () {
	var selectedItem = $('.assignees_select').val();
	targetProxy.assignees = selectedItem;
});
function showMergeable() {
	$('.only_mergeable_button').toggleClass('pressed');

	if (filters["mergeable"] == true){
	  targetProxy.mergeable = false;
	} else {
	  targetProxy.mergeable = true;
	}
}
$('tbody tr').hover(function(){
	$(this).find('td').addClass('hovered');
	}, function(){
	$(this).find('td').removeClass('hovered');
});
const searchFun = () => {
	let filter = document.getElementById('searchbar').value.toUpperCase();
	let dashboard = document.getElementById('Dashboard');
	let rows = dashboard.rows;
	for (i = 1; i < rows.length; i++) {  
	  let td = rows[i];
	  if(td){
	    let title = td.getElementsByClassName('title')[0]
	    let textvalue = title.textContent || title.innerHTML;
	      if(textvalue.toUpperCase().indexOf(filter) > -1) {
		rows[i].style.display = "";
	      }else{
		rows[i].style.display="none";
	      }
	  }
	}
}
function getTestsCounter(row, type){
	let info = row.getElementsByClassName('tests')[0].getElementsByClassName(type)[0];
	if (typeof(info) != 'undefined') {
	  return Number(info.id);
	}
	return Number('0');
}
function sortTable(column_) {
	var table;
	table = document.getElementById("Dashboard");
	var rows, i, x, y, count = 0;
	var switching = true;
	var sorted = false;
	// Order is set as ascending
	var direction = "descending";

	// Run loop until no switching is needed
	while (switching) {
	    switching = false;
	    var rows = table.rows;
	    //Loop to go through all rows
	    for (i = 1; i < (rows.length - 1); i++) {
		var Switch = false;

		// Fetch 2 elements that need to be compared
		if (column_ =="title"){
		  x = rows[i].getElementsByClassName("created_time")[0].getElementsByTagName('font')[0].children[0].outerHTML;
		  y = rows[i + 1].getElementsByClassName("created_time")[0].getElementsByTagName('font')[0].children[0].outerHTML;
		} else if (column_ =="updated") {
		  x = rows[i].getElementsByClassName('updated')[0].getElementsByTagName('font')[0].children[0].outerHTML;
		  y = rows[i + 1].getElementsByClassName('updated')[0].getElementsByTagName('font')[0].children[0].outerHTML;
		} else if (column_ == "changes") {
		  x = Number(rows[i].getElementsByClassName('changes')[0].id)
		  y = Number(rows[i+1].getElementsByClassName('changes')[0].id)
		} else if (column_ == "comments") {
		  x = Number(rows[i].getElementsByClassName('comments')[0].id)
		  y = Number(rows[i+1].getElementsByClassName('comments')[0].id)
		} else if (column_ == "tests") {
		  if (direction == "descending") {
		    let succ_1 = getTestsCounter(rows[i], "success");
		    let succ_2 = getTestsCounter(rows[i+1], "success");
		    if (succ_1 < succ_2) {
		      Switch = true;
		      break;
		    } else if (succ_1 == succ_2) {
		      let fail_1 = getTestsCounter(rows[i], "failure")+getTestsCounter(rows[i], "error");
		      let fail_2 = getTestsCounter(rows[i+1], "failure")+getTestsCounter(rows[i+1], "error");
		      if (fail_1 > fail_2) {
			Switch = true;
			break;
		      }
		    }
		  } else {
		    let fail_1 = getTestsCounter(rows[i], "failure")+getTestsCounter(rows[i], "error");
		    let fail_2 = getTestsCounter(rows[i+1], "failure")+getTestsCounter(rows[i+1], "error");
		    if (fail_1 < fail_2) {
		      Switch = true;
		      break;
		    } else if (fail_1 == fail_2) {
		      let succ_1 = getTestsCounter(rows[i], "success");
		      let succ_2 = getTestsCounter(rows[i+1], "success");
		      if (succ_1 > succ_2) {
			Switch = true;
			break;
		      }
		    }
		  }


		}
		// Check the direction of order
		if (direction == "ascending") {

		    // Check if 2 rows need to be switched
		    if (x > y)
			{
			// If yes, mark Switch as needed and break loop
			Switch = true;
			break;
		    }
		} else if (direction == "descending") {

		    // Check direction
		    if (x < y)
			{
			// If yes, mark Switch as needed and break loop
			Switch = true;
			break;
			}
		}
	    }
	    if (Switch) {
		// Function to switch rows and mark switch as completed
		rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
		switching = true;

		// Increase count for each switch
		count++;
	    } else {
		// Run while loop again for descending order
		if (count == 0 && direction == "descending") {
		      sorted = true;
		      direction = "ascending";
		      switching = true;
		}
	    }
	}
}
