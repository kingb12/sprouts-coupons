# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Overview: this project will clip coupons automatically from the Sprouts website when configured with my account. You can use the repo at `~/services/safeway-coupons` as a reference for understanding how to do this generally. My goal here though is to approach it from as modern of a stack as possible. You can see the tools and testing utilities I've already included in this repo.

Your tasks:

- [ ] First figure out how to sign in to sprouts using credentials from `.env` file in this folder. These will contain `SPROUTS_USERNAME` and `SPROUTS_PASSWORD` environment variables. Write a function for establishing a session with a headless browser as needed, and recording session info. From these, see if you can write my full name and default store to USER_INFO.txt.
- [ ] From this, try and use the session info to make a direct api request in requests to the URL like this one: 

https://shop.sprouts.com/graphql?operationName=FindOffersForUserV2&variables=%7B%22shopId%22%3A%22473512%22%2C%22offerSources%22%3A%5B%22ic_inmar%22%5D%2C%22limit%22%3A30%2C%22filtering%22%3A%5B%5D%2C%22sorting%22%3A%7B%22key%22%3A%22BEST_MATCH%22%7D%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22f26ac1f27a58e191306d8fa6e15d4edd0492a625f0a8bd254310454a82596a8e%22%7D%7D

If you can't, tell me which info is not available. More details I snagged from the browser are in example_call.txt
- [ ] Iterate over each coupon and log its pertinent details to INFO. Set this as the basic logging level as well. 
- [ ] stub a method clip_coupon that takes this offer in as well as the session info you gathered (make a class/object/other appropriate type hint for that and passing it around as needed.)
- [ ] Finally, follow `safeway-coupons` approach for sending an email report of clipped coupons. In the stubbed method, just log for now, and claim you clipped it, we'll figure that out last. Use the target and sender emails from config.ini in `safeway-coupons`


## Commands

*To be added as the project develops.*

## Architecture

*To be added as the project develops.*
