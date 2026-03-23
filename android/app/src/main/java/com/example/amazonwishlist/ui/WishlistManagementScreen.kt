package com.example.amazonwishlist.ui

import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.example.amazonwishlist.data.Wishlist
import com.example.amazonwishlist.data.WishlistApi
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun WishlistManagementScreen(onBack: () -> Unit) {
    val scope = rememberCoroutineScope()
    var wishlists by remember { mutableStateOf<List<Wishlist>>(emptyList()) }
    var isLoading by remember { mutableStateOf(true) }
    var showAddDialog by remember { mutableStateOf(false) }
    var newWishlistUrl by remember { mutableStateOf("") }
    var isAdding by remember { mutableStateOf(false) }

    fun loadWishlists() {
        scope.launch {
            isLoading = true
            try {
                wishlists = WishlistApi.retrofitService.getWishlists()
            } catch (e: Exception) {
                // Handle error
            } finally {
                isLoading = false
            }
        }
    }

    LaunchedEffect(Unit) {
        loadWishlists()
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Manage Wishlists", fontWeight = FontWeight.Bold) },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                    titleContentColor = MaterialTheme.colorScheme.onSurface,
                    navigationIconContentColor = MaterialTheme.colorScheme.onSurface
                ),
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.Default.ArrowBack, contentDescription = "Back")
                    }
                }
            )
        },
        floatingActionButton = {
            FloatingActionButton(onClick = { showAddDialog = true }) {
                Icon(Icons.Default.Add, contentDescription = "Add Wishlist")
            }
        }
    ) { padding ->
        Box(modifier = Modifier.padding(padding).fillMaxSize()) {
            if (isLoading) {
                CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))
            } else if (wishlists.isEmpty()) {
                Text(
                    text = "No custom wishlists added yet.",
                    modifier = Modifier.align(Alignment.Center),
                    style = MaterialTheme.typography.bodyLarge
                )
            } else {
                LazyColumn(modifier = Modifier.fillMaxSize()) {
                    items(wishlists) { wishlist ->
                        ListItem(
                            headlineContent = { Text(wishlist.name) },
                            supportingContent = { Text(wishlist.url, maxLines = 1) },
                            trailingContent = {
                                IconButton(onClick = {
                                    scope.launch {
                                        try {
                                            WishlistApi.retrofitService.deleteWishlist(wishlist.id)
                                            loadWishlists()
                                        } catch (e: Exception) {
                                            // Handle error
                                        }
                                    }
                                }) {
                                    Icon(Icons.Default.Delete, contentDescription = "Delete", tint = MaterialTheme.colorScheme.error)
                                }
                            }
                        )
                        HorizontalDivider()
                    }
                }
            }

            if (showAddDialog) {
                AlertDialog(
                    onDismissRequest = { if (!isAdding) showAddDialog = false },
                    title = { Text("Add Amazon Wishlist") },
                    text = {
                        Column {
                            Text("Paste the public Amazon Wishlist URL below:")
                            Spacer(modifier = Modifier.height(8.dp))
                            TextField(
                                value = newWishlistUrl,
                                onValueChange = { newWishlistUrl = it },
                                modifier = Modifier.fillMaxWidth(),
                                placeholder = { Text("https://www.amazon.es/hz/wishlist/ls/...") },
                                enabled = !isAdding
                            )
                        }
                    },
                    confirmButton = {
                        Button(
                            onClick = {
                                scope.launch {
                                    isAdding = true
                                    try {
                                        WishlistApi.retrofitService.addWishlist(mapOf("url" to newWishlistUrl))
                                        newWishlistUrl = ""
                                        showAddDialog = false
                                        loadWishlists()
                                    } catch (e: Exception) {
                                        // Handle error
                                    } finally {
                                        isAdding = false
                                    }
                                }
                            },
                            enabled = newWishlistUrl.isNotBlank() && !isAdding
                        ) {
                            if (isAdding) {
                                CircularProgressIndicator(modifier = Modifier.size(24.dp), color = MaterialTheme.colorScheme.onPrimary)
                            } else {
                                Text("Add")
                            }
                        }
                    },
                    dismissButton = {
                        TextButton(onClick = { showAddDialog = false }, enabled = !isAdding) {
                            Text("Cancel")
                        }
                    }
                )
            }
        }
    }
}
