import java.util.ArrayList;
import java.util.List;

public class ShoppingCart {

	private List<Item> items;
	
	public ShoppingCart(){
		this.items=new ArrayList<Item>();
	}
	
	public void addItem(Item item){
		this.items.add(item);
	}
	
	public void removeItem(Item item){
		this.items.remove(item);
	}
	
	public void payWithPaypal(String email,String password){
		if(items.isEmpty()) throw new RuntimeException("Your shopping cart is empty");
		int amount = 0;
		for(Item item : items){
			amount += item.getPrice();
		}
		
		String encryptedPassword= password.replaceAll(".", "*");
		System.out.println(amount + " euros paid using Paypal / email: " + email+ ", password: "+encryptedPassword);
	
		// vide le panier
		items= new ArrayList<Item>();
		System.out.println("Thank you and goodbye");
		System.out.println("------------------");
	}
	
	public void payWithCreditCard(String name, String cardNumber, String expiryDate) {
		if(items.isEmpty()) throw new RuntimeException("Your shopping cart is empty");
		int amount = 0;
		for(Item item : items){
			amount += item.getPrice();
		}
		
		String encryptedCardNumber= cardNumber.replaceAll(".", "*");
		System.out.println(amount + " euros paid using CreditCard / name: " + name+ ", card number: "+encryptedCardNumber+ " (expiration date: "+expiryDate+")");
		
		//vide le panier
		items= new ArrayList<Item>();
		System.out.println("Thank you and goodbye");
		System.out.println("------------------");
	}
}