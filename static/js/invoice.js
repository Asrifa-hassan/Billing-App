function existing_customer(){
    document.getElementById("existing-customer-div").style.display = "block";
    document.getElementById("new-customer-div").style.display = "none";
}


function new_customer(){
    document.getElementById("new-customer-div").style.display = "block";
    document.getElementById("existing-customer-div").style.display = "none";
}

function updatePrice(el) {
    const item = el.closest('.product_item'); // Find the closest product item row
    const product = item.querySelector('.product'); // Get the product select element
    const selectedOption = product.options[product.selectedIndex]; // Get the selected option
    const price = parseFloat(selectedOption.dataset.price || 0); // Get the price from data-price attribute
    console.log(price)
    // Find the price input field and update its value
    const priceInput = item.querySelector(".price");
    priceInput.value = price.toFixed(2); // Set the price input value

    const qty = parseFloat(item.querySelector(".qty").value || 1);
    const subTotalInput = item.querySelector(".sub_total");
    subTotalInput.value = (price * qty).toFixed(2);

    calculateTotal();
}


function addProduct(){
    const productItems = document.getElementById("product-items");
    const productItem = document.getElementById("product-item");
    const clone = productItem.cloneNode(true);

    // Reset values in the cloned row
    clone.querySelector(".product").selectedIndex = 0;
    clone.querySelector(".qty").value = 1;
    clone.querySelector(".price").value = "0.00";
    clone.querySelector(".sub_total").value = "0.00";
    productItems.appendChild(clone);

    // Attach event listeners to the cloned elements
    clone.querySelector(".product").addEventListener("change", function() {
        updatePrice(this);
    });

    clone.querySelector(".qty").addEventListener("input", function() {
        updatePrice(this.closest('.product_item').querySelector('.product'));
    });

    const removeButton = clone.querySelector(".btn-danger");
    removeButton.setAttribute("onclick","removeProduct(this)");
}

function calculateTotal(){
    const subTotals = document.querySelectorAll(".sub_total");
    let total = 0;

    subTotals.forEach(subTotals => {
        total += parseFloat(subTotals.value || 0);
    });

    const tax = total * 0.05;
    const grand_total = total + tax;


    document.getElementById("total").value = total.toFixed(2);
    document.getElementById("tax").value = tax.toFixed(2);
    document.getElementById("grand_total").value = grand_total.toFixed(2);

}

function removeProduct(el){
    const item = el.closest(".product_item");
    const productItems = document.getElementById("product-items");

    if (productItems.children.length > 1){
        item.remove();
        calculateTotal();
    }else{
        alert("At least one product must be present.");
    }

}

function setMaxStock(selectElement) {
    const selectedOption = selectElement.options[selectElement.selectedIndex];
    const stock = selectedOption.getAttribute('data-stock');

    // Find the same row
    const row = selectElement.closest('tr');
    const qtyInput = row.querySelector('.qty'); // Find qty input in this row

    if (stock) {
        qtyInput.max = stock;
    } else {
        qtyInput.removeAttribute('max');
    }
}