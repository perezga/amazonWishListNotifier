package com.example.amazonwishlist.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.unit.dp
import coil.compose.AsyncImage
import com.example.amazonwishlist.data.WishlistApi
import com.example.amazonwishlist.data.WishlistItem
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WishlistScreen() {
    val scope = rememberCoroutineScope()
    var items by remember { mutableStateOf<List<WishlistItem>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var errorMessage by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(Unit) {
        scope.launch {
            try {
                items = WishlistApi.retrofitService.getItems()
                isLoading = false
            } catch (e: Exception) {
                errorMessage = e.message
                isLoading = false
            }
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(title = { Text("Amazon Wishlist") })
        }
    ) { padding ->
        Box(modifier = Modifier.padding(padding)) {
            if (isLoading) {
                CircularProgressIndicator(modifier = Modifier.fillMaxSize().wrapContentSize())
            } else if (errorMessage != null) {
                Text(text = "Error: $errorMessage", color = MaterialTheme.colorScheme.error)
            } else {
                LazyColumn {
                    items(items) { item ->
                        WishlistItemCard(item)
                    }
                }
            }
        }
    }
}

@Composable
fun WishlistItemCard(item: WishlistItem) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .padding(8.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
    ) {
        Row(modifier = Modifier.padding(16.dp)) {
            AsyncImage(
                model = item.imageURL,
                contentDescription = null,
                modifier = Modifier.size(80.dp),
                contentScale = ContentScale.Fit
            )
            Spacer(modifier = Modifier.width(16.dp))
            Column {
                Text(text = item.title, style = MaterialTheme.typography.titleMedium, maxLines = 2)
                Spacer(modifier = Modifier.height(8.dp))
                Row {
                    Text(text = "Price: ${item.price ?: "N/A"}€", style = MaterialTheme.typography.bodyMedium)
                    Spacer(modifier = Modifier.width(16.dp))
                    Text(text = "Used: ${item.priceUsed ?: "N/A"}€", style = MaterialTheme.typography.bodyMedium)
                }
                if (item.savings > 0) {
                    Text(
                        text = "Savings: ${"%.2f".format(item.savings)}%",
                        color = MaterialTheme.colorScheme.primary,
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }
        }
    }
}
