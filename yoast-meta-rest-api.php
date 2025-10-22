<?php
/**
 * Plugin Name: Expose Yoast SEO Meta in REST
 * Description: Exposes Yoast SEO fields in REST API so they can be updated programmatically.
 * Version: 1.0
 * Author: Bala
 */


function expose_yoast_meta_in_rest() {
    $yoast_fields = [
        '_yoast_wpseo_focuskw',
        '_yoast_wpseo_title',
        '_yoast_wpseo_metadesc',
        '_yoast_wpseo_opengraph-title',
        '_yoast_wpseo_opengraph-description',
        '_yoast_wpseo_opengraph-image',
        '_yoast_wpseo_twitter-title',
        '_yoast_wpseo_twitter-description',
        '_yoast_wpseo_twitter-image',
    ];

    foreach ($yoast_fields as $field) {
        register_post_meta('page', $field, [
            'show_in_rest' => true,
            'single'       => true,
            'type'         => 'string',
        ]);
    }
}
add_action('init', 'expose_yoast_meta_in_rest');
